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

# --- ADVANCED UTILS ---

def clean_filename(name):
    """অপ্রয়োজনীয় ইউজারনেম ও লিঙ্ক মুছে ফেলে"""
    # Remove common patterns
    name = re.sub(r'@\w+|http\S+|\.com|\.me|\.in|www\S+|\[.*?\]|\(.*?\)', '', name)
    # Remove technical terms that shouldn't be in the clean title
    tech_patterns = r'1080p|720p|480p|HEVC|x264|x265|10bit|WEB-DL|HDRip|BluRay|WEBRip'
    name = re.sub(tech_patterns, '', name, flags=re.IGNORECASE)
    name = name.replace("_", " ").replace(".", " ").strip()
    return " ".join(name.split())

def get_file_info(update):
    """ফাইলের মেটাডেটা, ল্যাঙ্গুয়েজ, সাবটাইটেল এবং কোয়ালিটি ডিটেক্ট করে"""
    obj = update.video or update.document or update.audio
    if not obj: return None

    raw_name = getattr(obj, "file_name", "Unknown")
    
    # 1. ল্যাঙ্গুয়েজ ডিটেকশন (Extended)
    languages = []
    lang_map = {
        "HIN": "Hindi", "ENG": "English", "TAM": "Tamil", "TEL": "Telugu", 
        "MAL": "Malayalam", "BEN": "Bengali", "KAN": "Kannada", 
        "JAP": "Japanese", "CHI": "Chinese", "KOR": "Korean",
        "SPA": "Spanish", "FRE": "French", "GER": "German", "MAR": "Marathi", "GUJ": "Gujarati", "PUN": "Punjabi"
    }
    for key, value in lang_map.items():
        if re.search(rf'\b{key}\b|\b{value}\b', raw_name, re.IGNORECASE):
            languages.append(value)
    
    # Dual/Multi Audio logic
    if "DUAL" in raw_name.upper():
        audio_type = "Dual Audio"
    elif "MULTI" in raw_name.upper() or len(languages) > 2:
        audio_type = "Multi Audio"
    else:
        audio_type = languages[0] if languages else "Unknown"

    # 2. সাবটাইটেল ডিটেকশন
    subtitles = []
    if re.search(r'ESUB|ENGLISH-SUB', raw_name, re.IGNORECASE):
        subtitles.append("English")
    if re.search(r'HSUB|HINDI-SUB', raw_name, re.IGNORECASE):
        subtitles.append("Hindi")
    if re.search(r'BSUB|BENGALI-SUB', raw_name, re.IGNORECASE):
        subtitles.append("Bengali")
    if re.search(r'MSUB|M-SUB', raw_name, re.IGNORECASE):
        subtitles.append("Multi Sub")

    # 3. ভিডিও কোয়ালিটি ও টেকনিক্যাল ইনফো
    quality = "480p"
    if "2160" in raw_name or "4K" in raw_name.upper(): quality = "2160p (4K)"
    elif "1080" in raw_name: quality = "1080p"
    elif "720" in raw_name: quality = "720p"
    
    v_codec = "HEVC" if "HEVC" in raw_name.upper() or "x265" in raw_name.lower() else "x264"
    v_bit = "10Bit" if "10BIT" in raw_name.upper() else ""
    
    size = f"{round(obj.file_size / (1024 * 1024), 2)} MB"
    if obj.file_size > (1024**3):
        size = f"{round(obj.file_size / (1024**3), 2)} GB"

    # 4. সিজন এবং এপিসোড
    s_match = re.search(r'[Ss](\d+)|Season\s?(\d+)', raw_name, re.IGNORECASE)
    e_match = re.search(r'[Ee](\d+)|Episode\s?(\d+)', raw_name, re.IGNORECASE)
    ss_info = (s_match.group(1) or s_match.group(2)) if s_match else None
    ep_info = (e_match.group(1) or e_match.group(2)) if e_match else None

    # 5. ডিউরেশন
    duration = None
    if hasattr(obj, "duration") and obj.duration:
        duration = time.strftime('%H:%M:%S', time.gmtime(obj.duration))

    return {
        "file_name": clean_filename(raw_name),
        "quality": quality,
        "codec": f"{v_codec} {v_bit}".strip(),
        "size": size,
        "duration": duration,
        "format": raw_name.split(".")[-1].upper() if "." in raw_name else "MKV",
        "ep": ep_info,
        "ss": ss_info,
        "audio": audio_type,
        "subs": ", ".join(subtitles) if subtitles else "None",
        "year": re.search(r'(19|20)\d{2}', raw_name).group() if re.search(r'(19|20)\d{2}', raw_name) else None
    }

# --- HANDLERS ---

@app.on_chat_member_updated()
async def channel_join_log(bot, update):
    if update.new_chat_member and update.new_chat_member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.MEMBER]:
        me = await bot.get_me()
        if update.new_chat_member.user.id == me.id:
            chat = update.chat
            count = await bot.get_chat_members_count(chat.id)
            log_msg = (
                f"📡 **Added to New Channel!**\n\n"
                f"**Name:** `{chat.title}`\n"
                f"**ID:** `{chat.id}`\n"
                f"**Members:** `{count}`"
            )
            if LOG_CHANNEL:
                await bot.send_message(LOG_CHANNEL, log_msg)

@app.on_message(filters.private & filters.command("start"))
async def start_handler(bot, message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id)
        if LOG_CHANNEL:
            await bot.send_message(LOG_CHANNEL, f"👤 **New User!**\n**Name:** {message.from_user.mention}")
    
    if not await is_subscribed(bot, message):
        buttons = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_SUB}")]]
        return await message.reply_text("<b>Please join our channel to use me!</b>", reply_markup=InlineKeyboardMarkup(buttons))

    me = await bot.get_me()
    buttons = [[InlineKeyboardButton("➕ Add Me To Channel", url=f"https://t.me/{me.username}?startchannel=true")]]
    await message.reply_text(f"<b>Hello {message.from_user.mention}!</b>\nI am Advanced Auto Caption Bot.", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_message(filters.channel)
async def channel_handler(bot, update):
    if LOG_CHANNEL and update.chat.id == LOG_CHANNEL:
        return

    info = get_file_info(update)
    if not info: return

    # --- ADVANCED CAPTION DESIGN ---
    caption = f"📁 **File Name:** `{info['file_name']}`\n\n"
    
    if info['ss'] or info['ep']:
        caption += f"🎬 **Series Info:** `S{info['ss'] or '01'} - E{info['ep'] or 'Full'}`\n"
    
    caption += f"📊 **Quality:** `{info['quality']} | {info['codec']}`\n"
    caption += f"🔊 **Audio:** `{info['audio']}`\n"
    
    if info['subs'] != "None":
        caption += f"📝 **Subtitle:** `{info['subs']}`\n"
        
    caption += f"⚙️ **Size:** `{info['size']}`\n"
    
    if info['duration']:
        caption += f"⏱️ **Duration:** `{info['duration']}`\n"
    
    if info['year']:
        caption += f"📅 **Release:** `{info['year']}`\n"

    caption += f"\n✅ **Uploaded By: @{FORCE_SUB}**"

    try:
        await update.edit_caption(caption, parse_mode=enums.ParseMode.MARKDOWN)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await update.edit_caption(caption)
    except Exception as e:
        print(f"Error: {e}")

# --- ADMIN COMMANDS ---

@app.on_message(filters.private & filters.command("status") & filters.user(ADMIN_ID))
async def status_handler(bot, message):
    total = await db.total_users_count()
    await message.reply_text(f"📊 **Total Users:** `{total}`")

@app.on_message(filters.private & filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast_handler(bot, message):
    if not message.reply_to_message: return
    ms = await message.reply_text("Broadcasting...")
    all_users = await db.get_all_users()
    async for user in all_users:
        try: await message.reply_to_message.copy(user['id'])
        except: pass
    await ms.edit("✅ Broadcast Completed!")

async def is_subscribed(bot, message):
    if not FORCE_SUB: return True
    try:
        user = await bot.get_chat_member(FORCE_SUB, message.from_user.id)
        return user.status != enums.ChatMemberStatus.BANNED
    except: return False

async def start_bot():
    await app.start()
    print("Bot Started!")
    await pyrogram.idle()

if __name__ == "__main__":
    app.run(start_bot())
