# (c) @SGBACKUP
import pyrogram, os, asyncio, re, time
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, MessageNotModified, UserIsBlocked, InputUserDeactivated
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIGURATIONS ---
API_ID = int(os.environ.get("app_id", "26042863"))
API_HASH = os.environ.get("api_hash", "d4fabc00b0345cd3f0ccdc0c9b750f6e")
BOT_TOKEN = os.environ.get("bot_token", "")
FORCE_SUB = os.environ.get("FORCE_SUB", "SGBACKUP") 
# আপনার দেওয়া MongoDB URL সরাসরি যুক্ত করা হয়েছে
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://SGBACKUP:SGBACKUP@cluster0.64jkmog.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0") 
ADMIN_ID = int(os.environ.get("ADMIN_ID", "919169586")) 

# Database Setup
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client["AutoCaptionBot"]
user_db = db["users"]

app = Client("AutoCaptionBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- CAPTION TEMPLATE ---
CAPTION_TEXT = """📁 **File Name:** `{file_name}`

📊 **Quality:** {quality}
⚙️ **Size:** {size}
🎬 **Episode:** {ep} | **Season:** {ss}
🌐 **Language:** {lang}
📅 **Year:** {year}
⏱️ **Duration:** {duration}
📦 **Format:** {format}

✅ **Uploaded By: @SGBACKUP**"""

# --- UTILS ---
async def add_user(user_id):
    if not await user_db.find_one({"id": user_id}):
        await user_db.insert_one({"id": user_id})

def clean_filename(name):
    # অপ্রয়োজনীয় ইউজারনেম, লিঙ্ক এবং ব্র্যাকেট মুছে ফেলার জন্য
    name = re.sub(r'@\w+|http\S+|\.com|\.me|\.in|www\S+|\[.*?\]|\(.*?\)', '', name)
    name = name.replace("_", " ").replace(".", " ").strip()
    return " ".join(name.split())

def get_file_info(update):
    obj = update.video or update.document or update.audio
    if not obj: return None

    raw_name = getattr(obj, "file_name", "Unknown")
    clean_name = clean_filename(raw_name)

    # মেটাডেটা ডিটেকশন
    quality = "480p" if "480p" in raw_name else "720p" if "720p" in raw_name else "1080p" if "1080p" in raw_name else "HD"
    size = f"{round(obj.file_size / (1024 * 1024), 2)} MB"
    year_match = re.search(r'(19|20)\d{2}', raw_name)
    
    ep_match = re.search(r'[Ee][Pp][\s\._\-]?(\d+)', raw_name)
    ss_match = re.search(r'[Ss][Ee][Aa][Ss][Oo][Nn][\s\._\-]?(\d+)|[Ss](\d+)', raw_name)
    
    return {
        "file_name": clean_name,
        "quality": quality,
        "size": size,
        "duration": "N/A",
        "format": raw_name.split(".")[-1].upper() if "." in raw_name else "MKV",
        "ep": ep_match.group(1) if ep_match else "01",
        "ss": ss_match.group(1) or ss_match.group(2) if ss_match else "01",
        "lang": "Hindi-English",
        "year": year_match.group() if year_match else "N/A"
    }

# --- HANDLERS ---
@app.on_message(filters.private & filters.command("start"))
async def start_handler(bot, message):
    await add_user(message.from_user.id)
    await message.reply_text(
        f"<b>👋 Hello {message.from_user.mention}!</b>\n\nI am an Auto Caption Bot. Add me to your channel as admin to edit captions automatically.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Channel Updates", url=f"https://t.me/{FORCE_SUB}")]])
    )

@app.on_message(filters.private & filters.command("status") & filters.user(ADMIN_ID))
async def status_handler(bot, message):
    total = await user_db.count_documents({})
    await message.reply_text(f"<b>📊 Current Status</b>\n\nTotal Users: <code>{total}</code>")

@app.on_message(filters.private & filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast_handler(bot, message):
    if not message.reply_to_message:
        return await message.reply_text("<b>Reply to a message to broadcast!</b>")
    ms = await message.reply_text("<b>Broadcasting...</b>")
    success, failed = 0, 0
    async for user in user_db.find({}):
        try:
            await message.reply_to_message.copy(user["id"])
            success += 1
        except:
            failed += 1
        await asyncio.sleep(0.3)
    await ms.edit(f"<b>✅ Completed!</b>\n\nSuccess: {success}\nFailed: {failed}")

@app.on_message(filters.channel)
async def channel_handler(bot, update):
    info = get_file_info(update)
    if not info: return
    try:
        await update.edit_caption(CAPTION_TEXT.format(**info), parse_mode=enums.ParseMode.MARKDOWN)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await update.edit_caption(CAPTION_TEXT.format(**info))
    except: pass

print("Bot is Starting...")
app.run()
