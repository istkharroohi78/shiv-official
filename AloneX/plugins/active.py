# Copyright (c) 2026 THE SHIV
# Licensed under the MIT License.
# This file is part of MahiMusic
# DEVELOPER - THE SHIV

import os

from pyrogram import filters, types, enums

from AloneX import app, db, lang, queue

# Safe import for userbot to count assistant groups
try:
    from AloneX import userbot
except ImportError:
    userbot = None


# ==========================================
# 🟢 OLD ACTIVE VC COMMAND (UNTOUCHED)
# ==========================================
@app.on_message(filters.command(["ac", "activevc"]) & app.sudoers)
@lang.language()
async def _activevc(_, m: types.Message):
    if not db.active_calls:
        return await m.reply_text(m.lang["vc_empty"])

    if m.command[0] == "ac":
        return await m.reply_text(m.lang["vc_count"].format(len(db.active_calls)))

    sent = await m.reply_text(m.lang["vc_fetching"])
    text = ""

    for i, chat in enumerate(db.active_calls):
        playing = queue.get_current(chat)
        text += f"\n{i+1}. <code>{chat}</code>\n    ➜ {playing.title[:25]}"

    if len(text) < 4000:
        return await sent.edit_text(m.lang["vc_list"] + text)

    with open("activevc.txt", "w") as f:
        f.write(text)
    await sent.edit_media(
        media=types.InputMediaDocument(
            media="activevc.txt",
            caption=m.lang["vc_list"],
        )
    )
    os.remove("activevc.txt")


# ==========================================
# 🆕 /tvc - TOTAL VC WITH CHAT LINKS
# ==========================================
@app.on_message(filters.command(["tvc"]) & app.sudoers)
async def _tvc(_, m: types.Message):
    if not db.active_calls:
        return await m.reply_text("<blockquote><b>❌ ᴋᴏɪ ʙʜɪ ᴠᴏɪᴄᴇ ʏᴀ ᴠɪᴅᴇᴏ ᴄʜᴀᴛ ᴀᴄᴛɪᴠᴇ ɴᴀʜɪ ʜᴀɪ.</b></blockquote>")
        
    sent = await m.reply_text("<blockquote><b>⏳ ꜰᴇᴛᴄʜɪɴɢ ᴀᴄᴛɪᴠᴇ ᴠᴄ/ᴠɪᴅᴇᴏ ᴄʜᴀᴛ ᴅᴀᴛᴀ...</b></blockquote>")
    
    text = f"<blockquote><b>🎵 ᴛᴏᴛᴀʟ ᴀᴄᴛɪᴠᴇ ᴠᴄ / ᴠɪᴅᴇᴏ ᴄʜᴀᴛs : {len(db.active_calls)}</b>\n\n"
    
    for i, chat_id in enumerate(db.active_calls):
        playing = queue.get_current(chat_id)
        title = playing.title[:25] if playing else "Unknown Track"
        
        # Direct Private Link generation to avoid FloodWait limits
        chat_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/1"
        
        text += f"<b>{i+1}. ᴄʜᴀᴛ ɪᴅ :</b> <code>{chat_id}</code>\n"
        text += f"<b>🔗 ᴄʜᴀᴛ ʟɪɴᴋ :</b> <a href='{chat_link}'>ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ᴏᴘᴇɴ</a>\n"
        text += f"<b>🎧 ᴘʟᴀʏɪɴɢ :</b> {title}\n\n"
        
    text += "</blockquote>"

    if len(text) < 4000:
        return await sent.edit_text(text, disable_web_page_preview=True)
        
    # File fallback if list is too huge
    with open("tvc_data.txt", "w", encoding="utf-8") as f:
        clean_text = text.replace("<blockquote>", "").replace("</blockquote>", "").replace("<b>", "").replace("</b>", "").replace("<a href='", "").replace("'>ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ᴏᴘᴇɴ</a>", "")
        f.write("TOTAL ACTIVE VOICE CHATS DATA\n\n" + clean_text)
        
    await sent.edit_media(
        media=types.InputMediaDocument(
            media="tvc_data.txt",
            caption="<blockquote><b>🎵 ᴛᴏᴛᴀʟ ᴀᴄᴛɪᴠᴇ ᴠᴄ ʟɪsᴛ</b></blockquote>"
        )
    )
    os.remove("tvc_data.txt")


# ==========================================
# 🆕 /bdata - BOT & ASSISTANT GROUPS COUNT
# ==========================================
@app.on_message(filters.command(["bdata"]) & app.sudoers)
async def _bdata(_, m: types.Message):
    sent = await m.reply_text("<blockquote><b>⏳ ꜰᴇᴛᴄʜɪɴɢ ʙᴏᴛ & ᴀssɪsᴛᴀɴᴛ ᴅᴀᴛᴀ... (ᴛʜɪs ᴍᴀʏ ᴛᴀᴋᴇ ᴀ ꜰᴇᴡ sᴇᴄᴏɴᴅs)</b></blockquote>")
    
    bot_groups = 0
    bot_channels = 0
    ass_groups = 0
    
    # Bot Data Fetching
    try:
        async for dialog in app.get_dialogs():
            if dialog.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
                bot_groups += 1
            elif dialog.chat.type == enums.ChatType.CHANNEL:
                bot_channels += 1
    except Exception:
        pass

    # Assistant Data Fetching
    if userbot:
        try:
            # Agar aapka userbot instance kisi aur naam se hai toh 'one' ki jagah wo likhein
            client = getattr(userbot, 'one', None)
            if client:
                async for dialog in client.get_dialogs():
                    if dialog.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
                        ass_groups += 1
        except Exception:
            ass_groups = "Error fetching"
    else:
        ass_groups = "Not imported"

    text = (
        "<blockquote><b>📊 ᴍᴀʜɪ ᴍᴜsɪᴄ sᴛᴀᴛɪsᴛɪᴄs</b>\n\n"
        f"<b>🤖 ʙᴏᴛ ɪɴ ɢʀᴏᴜᴘs :</b> {bot_groups}\n"
        f"<b>📢 ʙᴏᴛ ɪɴ ᴄʜᴀɴɴᴇʟs :</b> {bot_channels}\n\n"
        f"<b>👤 ᴀssɪsᴛᴀɴᴛ ɪɴ ɢʀᴏᴜᴘs :</b> {ass_groups}</blockquote>"
    )
    
    await sent.edit_text(text)


# ==========================================
# 🆕 /tdata - TODAY'S ADD/REMOVE STATS
# ==========================================
@app.on_message(filters.command(["tdata"]) & app.sudoers)
async def _tdata(_, m: types.Message):
    try:
        added = await db.get_today_added_count()
        removed = await db.get_today_removed_count()
    except AttributeError:
        # Fallback agar MongoDB wale functions abhi db.py me nahi dale gaye
        added = "DB Setup Required"
        removed = "DB Setup Required"

    text = (
        "<blockquote><b>📈 ᴛᴏᴅᴀʏ's ɢʀᴏᴜᴘ ᴀᴄᴛɪᴠɪᴛʏ</b>\n\n"
        f"<b>✅ ᴀᴅᴅᴇᴅ ɪɴ ɢʀᴏᴜᴘs ᴛᴏᴅᴀʏ :</b> {added}\n"
        f"<b>❌ ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ ɢʀᴏᴜᴘs ᴛᴏᴅᴀʏ :</b> {removed}</blockquote>"
    )
    
    await m.reply_text(text)
