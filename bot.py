import sqlite3
import time
import re
import math

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ==========================================
# CONFIG
# ==========================================

TOKEN = ""

OWNER_ID = 6547160999

PAYMENT_LINK = "https://t.me/mlbbdiamond123/147"

# Group Username နဲ့ ထည့်ထားပါ
ORDER_GROUP_ID = "@mlbbdiamond139"

SCAM_WARNING = """
🚨 သတိပြုရန်

Admin စာပြန်နောက်ကျရင် လူလိမ်တွေ ပုံတုနဲ့ DM လာရင် Block လိုက်ပါ။

ကျွန်တော့် TG က @Kyawkyi198 တစ်ခုတည်းပါ။

DM ထဲလာသူရဲ့ Username ကို သေချာစစ်ပါ။

မသိရင် လုံးဝငွေမလွှဲပါနဲ့။
"""

# ==========================================
# DATABASE
# ==========================================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS settings(
key TEXT PRIMARY KEY,
value TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS warnings(
user_id INTEGER PRIMARY KEY,
last_time INTEGER
)
""")

conn.commit()

def set_setting(key, value):
    cur.execute("REPLACE INTO settings VALUES(?,?)", (key, str(value)))
    conn.commit()

def get_setting(key):
    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone()
    return row[0] if row else None

# ==========================================
# MLBB PRICE LIST
# ==========================================

MLBB_PRICES = {
    "55": 39.00, "165": 116.90, "275": 187.50, "565": 385.00, "wp": 76.00,
    "86": 61.50, "172": 122.00, "257": 177.50, "343": 239.00, "429": 299.50,
    "514": 355.00, "600": 416.50, "706": 480.00, "792": 541.50, "878": 602.00,
    "963": 657.50, "1049": 719.00, "1135": 779.50, "1220": 835.00,
    "2195": 1453.00, "3688": 2424.00, "5532": 3660.00, "9288": 6079.00
}

MCGG_PRICES = {
    "55": 40.00, "165": 120.00, "275": 200.00, "565": 400.00,
    "86": 62.50, "172": 125.00, "257": 187.00, "344": 250.00,
    "516": 375.00, "706": 500.00, "1346": 937.50, "1825": 1250.00,
    "2195": 1500.00, "3688": 2500.00, "5532": 3750.00, "9288": 6250.00, "wp": 99.90
}

# ==========================================
# ALIASES
# ==========================================

ALIASES = {
    "50+50": "55", "50+": "55", 
    "150+150": "165", "150+": "165",
    "250+250": "275", "250+": "275", 
    "500+500": "565", "500+": "565",
    "wp": "wp", "wkp": "wp", "weekly pass": "wp", "weeklypass": "wp"
}

ORDER_ALIASES = {
    "50+50": "55", "50+": "55",
    "150+150": "165", "150+": "165",
    "250+250": "275", "250+": "275",
    "500+500": "565", "500+": "565",
    "wp": "WP", "wkp": "WP", "weekly pass": "WP", "weeklypass": "WP"
}

# ==========================================
# HELPERS
# ==========================================

def round_ks(value):
    value = int(value)
    remainder = value % 50
    return value if remainder == 0 else value + (50 - remainder)

def calc_ks(coin_price, rate):
    return round_ks(coin_price * rate)

def calc_baht(ks, rate):
    return math.ceil(ks * rate)

def normalize_item(text):
    text = text.lower().strip()
    return ALIASES.get(text, text)

def normalize_order_item(item):
    item = item.lower().strip()
    if 'w' in item and 'p' in item:
        return "WP"
    if item in ORDER_ALIASES:
        return ORDER_ALIASES[item]
    return item.upper()

# ==========================================
# PRICE GENERATOR
# ==========================================

def build_mlbb_price_list(ks_rate, baht_rate):
    text = "📊 MLBB နောက်ဆုံးဈေး (KS + Baht)\n=============================\n"
    order = ["55", "165", "275", "565", "wp", "86", "172", "257", "343", "429",
             "514", "600", "706", "792", "878", "963", "1049", "1135", "1220",
             "2195", "3688", "5532", "9288"]
    for item in order:
        coin = MLBB_PRICES[item]
        ks = calc_ks(coin, ks_rate)
        baht = calc_baht(ks, baht_rate)
        if item == "wp":
            text += f"🔹 Weekly Pass = {ks:,} Ks ၊ {baht} Baht\n"
        else:
            text += f"🔹 {item} 💎 = {ks:,} Ks ၊ {baht} Baht\n"
    text += "============================="
    return text

def build_mcgg_price_list(ks_rate, baht_rate):
    text = "📊 MAGIC CHESS နောက်ဆုံးဈေး (KS + Baht)\n=============================\n"
    order = ["55", "165", "275", "565", "86", "172", "257", "344",
             "516", "706", "1346", "1825", "2195", "3688", "5532", "9288", "wp"]
    for item in order:
        coin = MCGG_PRICES[item]
        ks = calc_ks(coin, ks_rate)
        baht = calc_baht(ks, baht_rate)
        if item == "wp":
            text += f"🔹 Weekly Pass = {ks:,} Ks ၊ {baht} Baht\n"
        else:
            text += f"🔹 {item} 💎 = {ks:,} Ks ၊ {baht} Baht\n"
    text += "============================="
    return text

# ==========================================
# OWNER COMMANDS
# ==========================================

async def mlbb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    
    if not context.args:
        ks_rate = get_setting("mlbb_ks")
        baht_rate = get_setting("mlbb_baht")
        if not ks_rate or not baht_rate:
            await update.message.reply_text("⚠️ ဈေးနှုန်းသတ်မှတ်ချက် မရှိသေးပါ။\n\nပထမဆုံး /mlbb 19.2 0.00795 ဖြင့် သတ်မှတ်ပါ။")
            return
        ks_rate = float(ks_rate)
        baht_rate = float(baht_rate)
        text = build_mlbb_price_list(ks_rate, baht_rate)
        msg = await update.message.reply_text(text)
        try:
            old_pin = get_setting("mlbb_pin")
            if old_pin:
                try:
                    await context.bot.unpin_chat_message(chat_id=update.effective_chat.id, message_id=int(old_pin))
                except:
                    pass
            await context.bot.pin_chat_message(chat_id=update.effective_chat.id, message_id=msg.message_id)
            set_setting("mlbb_pin", msg.message_id)
        except:
            pass
        return
    
    try:
        ks_rate = float(context.args[0])
        baht_rate = float(context.args[1])
    except:
        await update.message.reply_text("Usage:\n/mlbb 19.2 0.00795\n\nသို့မဟုတ်\n/mlbb တစ်ခုတည်းနှိပ်ရုံဖြင့် ဈေးကြည့်ရန်။")
        return
    set_setting("mlbb_ks", ks_rate)
    set_setting("mlbb_baht", baht_rate)
    text = build_mlbb_price_list(ks_rate, baht_rate)
    msg = await update.message.reply_text(text)
    try:
        old_pin = get_setting("mlbb_pin")
        if old_pin:
            try:
                await context.bot.unpin_chat_message(chat_id=update.effective_chat.id, message_id=int(old_pin))
            except:
                pass
        await context.bot.pin_chat_message(chat_id=update.effective_chat.id, message_id=msg.message_id)
        set_setting("mlbb_pin", msg.message_id)
    except:
        pass

async def mcgg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    try:
        ks_rate = float(context.args[0])
        baht_rate = float(context.args[1])
    except:
        await update.message.reply_text("Usage:\n/mcgg 19.2 0.00795")
        return
    set_setting("mcgg_ks", ks_rate)
    set_setting("mcgg_baht", baht_rate)
    text = build_mcgg_price_list(ks_rate, baht_rate)
    await update.message.reply_text(text)

# ==========================================
# PRICE QUERY
# ==========================================

async def send_price_reply(message, item):
    item = normalize_item(item)
    if item not in MLBB_PRICES:
        return
    ks_rate = get_setting("mlbb_ks")
    baht_rate = get_setting("mlbb_baht")
    if not ks_rate or not baht_rate:
        return
    ks_rate = float(ks_rate)
    baht_rate = float(baht_rate)
    ks = calc_ks(MLBB_PRICES[item], ks_rate)
    baht = calc_baht(ks, baht_rate)
    if item == "wp":
        text = f"📊 Weekly Pass ဈေးနှုန်း\n\n💰 စျေးနှုန်း = {ks:,} Ks ၊ {baht} Baht\n\n⚠️ ယူမယ်ဆိုရင် ပုံနဲ့စာတွဲရေးပြီး ပို့ပေးပါဗျ။"
    else:
        text = f"📊 {item} 💎 ဈေးနှုန်း\n\n💰 စျေးနှုန်း = {ks:,} Ks ၊ {baht} Baht\n\n⚠️ ယူမယ်ဆိုရင် ပုံနဲ့စာတွဲရေးပြီး ပို့ပေးပါဗျ။"
    keyboard = [[InlineKeyboardButton("💸 ငွေလွှဲနံပတ်ကြည့်ရန်", url=PAYMENT_LINK)]]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def send_price_link(message):
    pin_id = get_setting("mlbb_pin")
    text = "✨ ဈေးကြည့်ရန် အောက်ပါလင့်ခ်ကိုနှိပ်ပါ\n\n"
    if pin_id:
        group_username = "mlbbdiamond139"
        text += f"📌 နောက်ဆုံး Pin လင့်ခ်:\nhttps://t.me/{group_username}/{pin_id}\n\n"
    text += "⚠️ ယူမယ့်ဟာကို ပုံနဲ့စာ တွဲရေးပြီး ပို့ပေးပါဗျ။"
    keyboard = [[InlineKeyboardButton("💸 ငွေလွှဲနံပတ်ကြည့်ရန်", url=PAYMENT_LINK)]]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ==========================================
# ORDER PARSER
# ==========================================

def parse_mlbb_order(text):
    text = text.strip()
    match = re.match(r"^(\d+)\s+(\d+)([A-Za-z0-9+\s]*)$", text, re.IGNORECASE)
    if not match:
        return None
    
    user_id = match.group(1)
    server_id = match.group(2)
    item_part = match.group(3).strip()
    
    if not item_part:
        return None
    
    first_word = item_part.split()[0] if ' ' in item_part else item_part
    item = normalize_order_item(first_word)
    
    valid_items = {"55", "165", "275", "565", "WP", "86", "172", "257", "343", "429",
                   "514", "600", "706", "792", "878", "963", "1049", "1135", "1220",
                   "2195", "3688", "5532", "9288"}
    
    return (user_id, server_id, item) if item in valid_items else None

def parse_pubg_order(text):
    parts = text.strip().split()
    if len(parts) != 2 or not parts[0].isdigit():
        return None
    pubg_items = ["60", "325", "660", "1800", "3850", "8100"]
    return (parts[0], parts[1]) if parts[1] in pubg_items else None

ORDER_WARNING = """
⚠️ ID Zone Item ပုံစံဖြင့် တစ်ခါတည်း တွဲပို့ပေးပါရန်။
ဥပမာ - 46464646 4646 WP (ID နဲ့ Zone ID ကြား Space ခွာပေးပါ)
"""

# ==========================================
# SCAM WARNING
# ==========================================

def should_send_warning(user_id):
    cur.execute("SELECT last_time FROM warnings WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    now = int(time.time())
    if not row:
        cur.execute("INSERT OR REPLACE INTO warnings VALUES(?,?)", (user_id, now))
        conn.commit()
        return True
    if now - row[0] >= 300:
        cur.execute("UPDATE warnings SET last_time=? WHERE user_id=?", (now, user_id))
        conn.commit()
        return True
    return False

# ==========================================
# PROCESS ORDER (NO FORWARD)
# ==========================================

def get_item_price(item):
    ks_rate = get_setting("mlbb_ks")
    baht_rate = get_setting("mlbb_baht")
    if not ks_rate or not baht_rate:
        return "Price not set"
    ks_rate = float(ks_rate)
    baht_rate = float(baht_rate)
    if item == "WP":
        coin_price = MLBB_PRICES["wp"]
    else:
        coin_price = MLBB_PRICES[item.lower()]
    ks = calc_ks(coin_price, ks_rate)
    baht = calc_baht(ks, baht_rate)
    return f"{ks:,} Ks ({baht} Baht)"

async def process_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    
    if not msg.photo:
        if msg.text and re.match(r"^\d+\s+\d+", msg.text.strip()):
            await msg.reply_text(ORDER_WARNING)
        return
    
    if not msg.caption:
        await msg.reply_text(ORDER_WARNING)
        return
    
    caption = msg.caption.strip()
    mlbb = parse_mlbb_order(caption)
    pubg = parse_pubg_order(caption)
    
    if not mlbb and not pubg:
        await msg.reply_text(ORDER_WARNING)
        return
    
    
    try:
        # Get user info
        user = msg.from_user
        username = f"@{user.username}" if user.username else f"{user.first_name}"
        user_link = f"[{username}](tg://user?id={user.id})"
        
        # Prepare order message text
        if mlbb:
            user_id, server_id, item = mlbb
            price_text = get_item_price(item)
            order_text = f"""🆕 **New Order!**

👤 Customer: {user_link}
📱 Game: MLBB
🆔 ID: {user_id}
🌐 Zone: {server_id}
✨ Item: {item}
💰 Price: {price_text}

📸 Order screenshot attached below."""
            
            buttons = [
                InlineKeyboardButton("✅ လက်ခံ", callback_data=f"accept_mlbb:{msg.chat.id}:{msg.message_id}:{user_id}:{server_id}:{item}"),
                InlineKeyboardButton("❌ ငြင်းပယ်", callback_data=f"reject:{msg.chat.id}:{msg.message_id}")
            ]
        else:
            user_id, item = pubg
            order_text = f"""🆕 **New Order!**

👤 Customer: {user_link}
📱 Game: PUBG
🆔 ID: {user_id}
✨ Item: {item} UC

📸 Order screenshot attached below."""
            
            buttons = [
                InlineKeyboardButton("✅ လက်ခံ", callback_data=f"accept_pubg:{msg.chat.id}:{msg.message_id}:{user_id}:{item}"),
                InlineKeyboardButton("❌ ငြင်းပယ်", callback_data=f"reject:{msg.chat.id}:{msg.message_id}")
            ]
        
        # Send photo with caption to group
        photo_file_id = msg.photo[-1].file_id
        await context.bot.send_photo(
            chat_id=ORDER_GROUP_ID,
            photo=photo_file_id,
            caption=order_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([buttons])
        )
        
    except Exception as e:
        await msg.reply_text(f"❌ Group ထဲပို့ရာတွင် အမှားဖြစ်နေပါသည်။\nError: {e}")

# ==========================================
# BUTTON HANDLER
# ==========================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    data = query.data
    
    if query.from_user.id != OWNER_ID:
        await query.answer("Admin မှသာနှိပ်လို့ရပါသည်။", show_alert=True)
        return
    
    await query.answer()
    parts = data.split(":")
    
    if data.startswith("reject:"):
        chat_id = int(parts[1])
        msg_id = int(parts[2])
        await context.bot.send_message(chat_id=chat_id, reply_to_message_id=msg_id, text="❌ အော်ဒါကို ငြင်းပယ်လိုက်ပါသည်။\nAdmin ကို ဆက်သွယ်ပေးပါ။")
        await query.edit_message_reply_markup(reply_markup=None)
    
    elif data.startswith("accept_mlbb:"):
        chat_id = int(parts[1])
        msg_id = int(parts[2])
        user_id = parts[3]
        server_id = parts[4]
        item = parts[5]
        price_text = get_item_price(item)
        await context.bot.send_message(chat_id=chat_id, reply_to_message_id=msg_id, text=f"✅ ထည့်ပြီးပါပြီ ကျေးဇူးတင်ပါသည်။\n\n{user_id} {server_id} {item}\n💰 {price_text}")
        await query.edit_message_reply_markup(reply_markup=None)
    
    elif data.startswith("accept_pubg:"):
        chat_id = int(parts[1])
        msg_id = int(parts[2])
        user_id = parts[3]
        item = parts[4]
        await context.bot.send_message(chat_id=chat_id, reply_to_message_id=msg_id, text=f"✅ ထည့်ပြီးပါပြီ ကျေးဇူးတင်ပါသည်။\n\nID: {user_id}\nItem: {item} UC")
        await query.edit_message_reply_markup(reply_markup=None)

# ==========================================
# START
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ KaiO Calculator Bot Online")

# ==========================================
# CUSTOMER MESSAGE
# ==========================================

async def customer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    text = update.message.text.strip()
    low = text.lower()
    
    if low == "ဈေး" or low == "price":
        await send_price_link(update.message)
        return
    
    price_items = ["55", "165", "275", "565", "wp", "86", "172", "257", "343", "429",
                   "514", "600", "706", "792", "878", "963", "1049", "1135", "1220",
                   "2195", "3688", "5532", "9288", "50+50", "50+", "150+150", "150+",
                   "250+250", "250+", "500+500", "500+", "wkp", "weekly pass", "weeklypass"]
    
    if low in price_items:
        await send_price_reply(update.message, low)

# ==========================================
# ALL MESSAGES
# ==========================================

async def all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    
    if should_send_warning(update.message.from_user.id):
        await update.message.reply_text(SCAM_WARNING)
    
    await process_order(update, context)
    await customer_message(update, context)

# ==========================================
# MAIN
# ==========================================

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mlbb", mlbb))
    app.add_handler(CommandHandler("mcgg", mcgg))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, all_messages))
    
    print("BOT STARTED")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
