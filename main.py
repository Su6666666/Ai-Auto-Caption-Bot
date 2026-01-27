# (c) @SGBACKUP
import pyrogram, os, asyncio, re, time
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, MessageNotModified, UserIsBlocked, InputUserDeactivated
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db 

# --- CONFIGURATIONS ---
API_ID = int(os.environ.get("app_id", "26042863"))
API_HASH = os.environ.get("api_hash", "d4fabc00b0345cd3f0ccdc0c9b750f6e")
BOT_TOKEN = os.environ.get("bot_token", "")
FORCE_SUB = os.environ.get("FORCE_SUB", "SGBACKUP") 
ADMIN_ID = int(os.environ.get("ADMIN_ID", "919169586")) 
# আপনার দেওয়া লগ চ্যানেল আইডি এখানে অ্যাড করা হয়েছে
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1001994332079"))

app = Client("AutoCaptionBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- UTILS ---
def clean_filename(name):
    # অপ্রয়োজনীয় ইউজারনেম, লিঙ্ক এবং ব্র্যাকেট মুছে ফেলে
    name = re.sub(r'@\w+|http\S+|\.com|\.me|\.in|www\S+|\[.*?\]|\(.*?\)', '', name)
    name = name.replace("_", " ").replace(".", " ").strip()
    return " ".join(name.split())

def get_file_info(update):
    obj = update.video or update.document or update.audio
    if not obj: return None

    raw_name = getattr(obj, "file_name", "Unknown")
    clean_name = clean_filename(raw_name)

    quality = "1080p" if "1080p" in raw_name else "720p" if "720p" in raw_name else "480p" if "480p" in raw_name else "HD"
    size = f"{round(obj.file_size / (1024 * 1024), 2)} MB"
    year_match = re.search(r'(19|20)\d{2}', raw_name)
    
    # এপিসোড, সিজন এবং কম্বাইন্ড ডিটেকশন
    is_combined = "COMBINED" in raw_name.upper()
    ep_match = re.search(r'[Ee][Pp][\s\._\-]?(\d+)', raw_name)
    ss_match = re.search(r'[Ss][Ee][Aa][Ss][Oo][Nn][\s\._\-]?(\d+)|[Ss](\d+)', raw_name)
    
    return {
        "file_name": clean_name,
        "quality": quality,
        "size": size,
        "duration": "N/A",
        "format": raw_name.split(".")[-1].upper() if "." in raw_name else "MKV",
        "ep": "COMBINED" if is_combined else (ep_match.group(1) if ep_match else None),
        "ss": "COMBINED" if is_combined else (ss_match.group(1) or ss_match.group(2) if ss_match else None),
        "lang": "Hindi-English",
        "year": year_match.group() if year_match else "N/A"
    }

# --- HANDLERS ---
@app.on_message(filters.private & filters.command("start"))
async def start_handler(bot, message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id)
    await message.reply_text(
        f"<b>Hello {message.from_user.mention}!</b>\n\nI am a professional Auto Caption Bot. Add me to your channel as admin.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Channel Updates", url=f"https://t.me/{FORCE_SUB}")]])
    )

@app.on_message(filters.private & filters.command("status") & filters.user(ADMIN_ID))
async def status_handler(bot, message):
    total = await db.total_users_count()
    await message.reply_text(f"<b>📊 Current Status</b>\n\nTotal Users in DB: <code>{total}</code>")

@app.on_message(filters.private & filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast_handler(bot, message):
    if not message.reply_to_message:
        return await message.reply_text("<b>Reply to a message to broadcast!</b>")
    ms = await message.reply_text("<b>Broadcasting...</b>")
    all_users = await db.get_all_users()
    success, failed = 0, 0
    async for user in all_users:
        try:
            await message.reply_to_message.copy(user['id'])
            success += 1
        except:
            await db.delete_user(user['id'])
            failed += 1
        await asyncio.sleep(0.3)
    await ms.edit(f"<b>✅ Completed!</b>\n\nSuccess: {success}\nFailed: {failed}")

@app.on_message(filters.channel)
async def channel_handler(bot, update):
    info = get_file_info(update)
    if not info: return

    # ডায়নামিক ক্যাপশন বিল্ডার (মুভি হলে এপিসোড/সিজন হাইড হবে)
    caption = f"📁 **File Name:** `{info['file_name']}`\n\n"
    caption += f"📊 **Quality:** {info['quality']}\n"
    caption += f"⚙️ **Size:** {info['size']}\n"
    
    # মুভি হলে সিজন/এপিসোড থাকবে না, ওয়েব সিরিজ বা কম্বাইন্ড হলে দেখাবে
    if info['ep'] or info['ss']:
        caption += f"🎬 **Episode:** {info['ep'] or 'N/A'} | **Season:** {info['ss'] or 'N/A'}\n"
    
    caption += f"🌐 **Language:** {info['lang']}\n"
    caption += f"📅 **Year:** {info['year']}\n"
    caption += f"⏱️ **Duration:** {info['duration']}\n"
    caption += f"📦 **Format:** {info['format']}\n\n"
    caption += f"✅ **Uploaded By: @SGBACKUP**"

    try:
        await update.edit_caption(caption, parse_mode=enums.ParseMode.MARKDOWN)
        # লগ চ্যানেলে মেসেজ ফরোয়ার্ড করা
        if LOG_CHANNEL:
            await update.copy(LOG_CHANNEL, caption=caption)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await update.edit_caption(caption)
    except: pass

print("Bot with LOG Channel & Smart Detection Started!")
app.run()
