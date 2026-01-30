# (c) @SGBACKUP
import pyrogram, os, asyncio, re, time
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db 

# --- CONFIGURATIONS ---
API_ID = int(os.environ.get("app_id", "26042863"))
API_HASH = os.environ.get("api_hash", "d4fabc00b0345cd3f0ccdc0c9b750f6e")
BOT_TOKEN = os.environ.get("bot_token", "")
FORCE_SUB = os.environ.get("FORCE_SUB", "SGBACKUP") 
ADMIN_ID = int(os.environ.get("ADMIN_ID", "919169586")) 
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1001994332079"))
OWNER_LINK = "https://t.me/SubhajitGhosh0"

app = Client("AutoCaptionBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- UTILS ---
async def is_subscribed(bot, message):
    """ইউজার চ্যানেলে জয়েন আছে কি না চেক করার জন্য"""
    if not FORCE_SUB:
        return True
    try:
        user = await bot.get_chat_member(FORCE_SUB, message.from_user.id)
        if user.status == enums.ChatMemberStatus.BANNED:
            return False
        return True
    except UserNotParticipant:
        return False
    except Exception:
        return True

def clean_filename(name):
    """অপ্রয়োজনীয় ইউজারনেম ও লিঙ্ক মুছে ফেলে"""
    name = re.sub(r'@\w+|http\S+|\.com|\.me|\.in|www\S+|\[.*?\]|\(.*?\)', '', name)
    name = name.replace("_", " ").replace(".", " ").strip()
    return " ".join(name.split())

def get_file_info(update):
    """ফাইলের মেটাডেটা, সিজন, এপিসোড এবং সাবটাইটেল বের করে"""
    obj = update.video or update.document or update.audio
    if not obj: return None

    raw_name = getattr(obj, "file_name", "Unknown")
    clean_name = clean_filename(raw_name)

    # ল্যাঙ্গুয়েজ ডিটেকশন
    languages = []
    lang_map = {
        "HIN": "Hindi", "ENG": "English", "TAM": "Tamil", "TEL": "Telugu", 
        "MAL": "Malayalam", "BEN": "Bengali", "KAN": "Kannada", 
        "JAP": "Japanese", "CHI": "Chinese"
    }
    for key, value in lang_map.items():
        if key in raw_name.upper() or value.upper() in raw_name.upper():
            languages.append(value)

    # সাবটাইটেল ডিটেকশন (ESUB, HSUB, JSUB, CSUB, BSUB)
    subtitles = []
    sub_map = {
        "ESUB": "English", "HSUB": "Hindi", "JSUB": "Japanese", 
        "CSUB": "Chinese", "BSUB": "Bengali", "SUB": "Available"
    }
    for key, value in sub_map.items():
        if key in raw_name.upper():
            subtitles.append(value)

    quality = "1080p" if "1080p" in raw_name else "720p" if "720p" in raw_name else "480p" if "480p" in raw_name else "HD"
    size = f"{round(obj.file_size / (1024 * 1024), 2)} MB"
    year_match = re.search(r'(19|20)\d{2}', raw_name)
    
    duration = None
    if hasattr(obj, "duration") and obj.duration:
        duration = time.strftime('%H:%M:%S', time.gmtime(obj.duration))
    
    # স্মার্ট সিজন এবং এপিসোড ডিটেকশন
    ss_info = None
    ep_info = None
    
    s_match = re.search(r'[Ss](\d+)|Season\s?(\d+)', raw_name, re.IGNORECASE)
    if s_match:
        ss_info = s_match.group(1) or s_match.group(2)
    
    e_match = re.search(r'[Ee](\d+)|Episode\s?(\d+)', raw_name, re.IGNORECASE)
    if e_match:
        ep_info = e_match.group(1) or e_match.group(2)

    if "COMBINED" in raw_name.upper():
        ep_info = "COMBINED"
        if not ss_info:
            ss_info = "01" 

    return {
        "file_name": clean_name, "quality": quality, "size": size,
        "duration": duration, "format": raw_name.split(".")[-1].upper() if "." in raw_name else "MKV",
        "ep": ep_info, "ss": ss_info, "lang": languages, "sub": subtitles,
        "year": year_match.group() if year_match else None
    }

# --- HANDLERS ---

@app.on_chat_member_updated()
async def channel_join_log(bot, update):
    if update.new_chat_member and update.new_chat_member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.MEMBER]:
        me = await bot.get_me()
        if update.new_chat_member.user.id == me.id:
            chat = update.chat
            count = await bot.get_chat_members_count(chat.id)
            invite = "No Link Available"
            try:
                invite = await bot.export_chat_invite_link(chat.id)
            except: pass

            log_msg = (
                f"📡 **Added to New Channel!**\n\n"
                f"**Name:** `{chat.title}`\n"
                f"**ID:** `{chat.id}`\n"
                f"**Members:** `{count}`\n"
                f"**Link:** {invite}"
            )
            if LOG_CHANNEL:
                await bot.send_message(LOG_CHANNEL, log_msg)

@app.on_message(filters.private & filters.command("start"))
async def start_handler(bot, message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id)
        if LOG_CHANNEL:
            await bot.send_message(LOG_CHANNEL, f"👤 **New User Joined!**\n**Name:** {message.from_user.mention}\n**ID:** `{message.from_user.id}`")
    
    if not await is_subscribed(bot, message):
        buttons = [
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_SUB}")],
            [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{(await bot.get_me()).username}?start=true")]
        ]
        return await message.reply_text(
            f"<b>👋 Hello {message.from_user.mention}</b>\n\nYou must join our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    me = await bot.get_me()
    buttons = [
        [InlineKeyboardButton("➕ Add Me To Your Channel", url=f"https://t.me/{me.username}?startchannel=true")],
        [InlineKeyboardButton("👨‍💻 Owner", url=OWNER_LINK)]
    ]
    await message.reply_text(
        f"<b>👋 Hello {message.from_user.mention}</b>\n\nI am an Ai Auto Caption Bot.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_message(filters.channel)
async def channel_handler(bot, update):
    if LOG_CHANNEL and update.chat.id == LOG_CHANNEL:
        return

    info = get_file_info(update)
    if not info: return

    caption = f"📁 **File Name:** `{info['file_name']}`\n\n"
    caption += f"📊 **Quality:** {info['quality']}\n"
    caption += f"⚙️ **Size:** {info['size']}\n"
    
    if info['ep'] or info['ss']:
        caption += f"🎬 **Episode:** {info['ep'] or 'N/A'} | **Season:** {info['ss'] or 'N/A'}\n"
    
    if info['lang']:
        caption += f"🌐 **Language:** {'-'.join(info['lang'])}\n"

    # নতুন সাবটাইটেল ফিচার (যা পাওয়া যাবে না, সেই লাইনটি আসবে না)
    if info['sub']:
        caption += f"📜 **Subtitle:** {'-'.join(info['sub'])}\n"
    
    if info['year']:
        caption += f"📅 **Year:** {info['year']}\n"
        
    if info['duration']:
        caption += f"⏱️ **Duration:** {info['duration']}\n"
    
    caption += f"📦 **Format:** {info['format']}\n\n"
    caption += f"✅ **Uploaded By: @SGBACKUP**"

    try:
        await update.edit_caption(caption, parse_mode=enums.ParseMode.MARKDOWN)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await update.edit_caption(caption)
    except: pass

@app.on_message(filters.private & filters.command("status") & filters.user(ADMIN_ID))
async def status_handler(bot, message):
    total = await db.total_users_count()
    await message.reply_text(f"📊 <b>Current Status:</b> <code>{total} Users</code>")

@app.on_message(filters.private & filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast_handler(bot, message):
    if not message.reply_to_message: return
    ms = await message.reply_text("Broadcasting...")
    all_users = await db.get_all_users()
    async for user in all_users:
        try: await message.reply_to_message.copy(user['id'])
        except: pass
    await ms.edit("✅ Broadcast Completed!")

async def start_bot():
    await app.start()
    if LOG_CHANNEL:
        try: await app.send_message(LOG_CHANNEL, "🚀 **Auto Caption Bot Started Successfully!**")
        except: pass
    await pyrogram.idle()

if __name__ == "__main__":
    app.run(start_bot())
