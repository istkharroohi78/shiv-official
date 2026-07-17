# Copyright (c) 2026 THE SHIV
# Licensed under the MIT License.
# This file is part of MahiMusic
# DEVELOPER - THE SHIV

import asyncio
from collections import defaultdict

from ntgcalls import (ConnectionNotFound, TelegramServerError,
                      RTMPStreamingUnsupported)
from pyrogram.errors import MessageIdInvalid, FloodWait, MessageNotModified
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from AloneX import app, config, db, lang, logger, queue, userbot, yt
from AloneX.helpers import Media, Track, buttons, thumb, utils, vclogger


async def _delete_msg(msg: Message, delay: int = 6):
    try:
        await asyncio.sleep(delay)
        await msg.delete()
    except Exception:
        pass


class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []
        self.history: dict[int, list[str]] = defaultdict(list)
        self.pending_autoplay: dict[int, Track] = {}
        self.autoplay_prefetching: set[int] = set()
        self.autoplay_failures: dict[int, int] = defaultdict(int)

    async def _prefetch_next(self, chat_id: int) -> None:
        if chat_id in self.autoplay_prefetching:
            return
        self.autoplay_prefetching.add(chat_id)
        try:
            await asyncio.sleep(3) 
            try:
                q = queue.get(chat_id)
                if q and isinstance(q, list) and len(q) > 1:
                    next_track = q[1]
                    # ✅ MEMORY FIX: Removed background downloading
                    # if not next_track.file_path:
                    #     next_track.file_path = await yt.download(next_track.id, video=next_track.video)
                    return 
            except Exception:
                pass

            if await db.get_autoplay(chat_id):
                current = queue.get_current(chat_id)
                if current and isinstance(current, Track):
                    related = await yt.get_related(current, self.history[chat_id])
                    if related:
                        # ✅ MEMORY FIX: Removed background downloading for autoplay
                        # related.file_path = await yt.download(related.id, video=related.video)
                        self.pending_autoplay[chat_id] = related
        except Exception:
            pass

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        try:
            await db.playing(chat_id, paused=True)
        except:
            pass
        return await client.pause(chat_id)

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        try:
            await db.playing(chat_id, paused=False)
        except:
            pass
        return await client.resume(chat_id)

    async def stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)
        self.autoplay_failures[chat_id] = 0
        try:
            queue.clear(chat_id)
            await db.remove_call(chat_id)
        except:
            pass
        self.history.pop(chat_id, None)
        self.pending_autoplay.pop(chat_id, None)
        self.autoplay_prefetching.discard(chat_id)
        vclogger.clear_chat(chat_id)
        try:
            await client.leave_call(chat_id, close=False)
        except:
            pass

    async def play_media(self, chat_id: int, message: Message, media: Media | Track, seek_time: int = 0) -> None:
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        _thumb = await thumb.generate(media) if isinstance(media, Track) else config.DEFAULT_THUMB

        if not media.file_path:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            return await self.play_next(chat_id)

        stream = types.MediaStream(
            media_path=media.file_path,
            audio_parameters=types.AudioQuality.HIGH,
            video_parameters=types.VideoQuality.HD_720p,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=(types.MediaStream.Flags.AUTO_DETECT if media.video else types.MediaStream.Flags.IGNORE),
            ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
        )
        try:
            await client.play(chat_id=chat_id, stream=stream, config=types.GroupCallConfig(auto_start=False))
            if not seek_time:
                media.time = 1
                await db.add_call(chat_id)
                play_type = "🎬 Video" if media.video else "🎧 Audio"
                linked_title = f"<a href='{media.url}'>{media.title}</a>"
                text = _lang["play_media"].format(media.url, linked_title, media.duration, media.user, play_type)
                start_timer = f"00:00 {media.duration}"
                keyboard = buttons.controls(chat_id, timer=start_timer)
                
                try:
                    active_msg = await message.edit_media(media=InputMediaPhoto(media=_thumb, caption=text), reply_markup=keyboard)
                except MessageIdInvalid:
                    active_msg = await app.send_photo(chat_id=chat_id, photo=_thumb, caption=text, reply_markup=keyboard)
                media.message_id = active_msg.id
                
                asyncio.create_task(self._prefetch_next(chat_id))

        except Exception:
            await self.play_next(chat_id)

    async def play_next(self, chat_id: int) -> None:
        current = queue.get_current(chat_id)
        if current:
            history = self.history[chat_id]
            history.append(current.id)
            del history[:-20]

        self.autoplay_prefetching.discard(chat_id)
        media = queue.get_next(chat_id)
        
        if not media:
            if current and isinstance(current, Track) and await db.get_autoplay(chat_id):
                related = self.pending_autoplay.pop(chat_id, None)

                if not related:
                    try:
                        related = await yt.get_related(current, self.history[chat_id])
                    except Exception:
                        related = None

                if not related:
                    self.autoplay_failures[chat_id] += 1
                    if self.autoplay_failures[chat_id] >= 4:
                        await app.send_message(chat_id, "⚠️ Autoplay failed 4 times. Stopping stream.")
                        return await self.stop(chat_id)
                else:
                    self.autoplay_failures[chat_id] = 0

                if related:
                    related.user = "Autoplay"
                    queue.add(chat_id, related)
                    media = queue.get_current(chat_id)
                    short_title = media.title[:45] + "..." if len(media.title) > 45 else media.title
                    matched_title = current.title[:45] + "..." if current and current.title else "Unknown Track"
                    
                    # 1. Chat me normal notice 
                    notice = await app.send_message(chat_id=chat_id, text=f"<blockquote>▶️ <b>Aᴜᴛᴏᴘʟᴀʏ Nᴇxᴛ :</b>\n🎧 <a href='{media.url}'><i>{short_title}</i></a></blockquote>", disable_web_page_preview=True)
                    asyncio.create_task(_delete_msg(notice, 6))

                    # 2. LOGGER GROUP ME DETAILED LOG (As per your Screenshot)
                    try:
                        chat_info = await app.get_chat(chat_id)
                        chat_title = chat_info.title
                    except Exception:
                        chat_title = "Unknown Chat"

                    log_text = (
                        f"<blockquote><b>🔁 AUTO-PLAY TRACK STARTED</b>\n\n"
                        f"<b>🥀 GROUP :</b> {chat_title} [{chat_id}]\n"
                        f"<b>🎵 PLAYING :</b> <a href='{media.url}'>{short_title}</a>\n"
                        f"<b>🔗 MATCHED WITH :</b> {matched_title}\n"
                        f"<b>⏭ UPCOMING :</b> Autoplay will decide next...</blockquote>"
                    )
                    
                    try:
                        if hasattr(config, "LOGGER_ID") and config.LOGGER_ID:
                            await app.send_message(
                                chat_id=config.LOGGER_ID, 
                                text=log_text, 
                                disable_web_page_preview=True
                            )
                    except Exception:
                        pass
                    # ----------------------------------------------------

            if not media:
                return await self.stop(chat_id)

        _lang = await lang.get_lang(chat_id)
        if not media.file_path:
            msg = await app.send_message(chat_id=chat_id, text=_lang["play_next"])
            media.file_path = await yt.download(media.id, video=media.video)
        else:
            msg = await app.send_message(chat_id=chat_id, text="⚡")

        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)

    async def ping(self) -> float:
        pings = [client.ping for client in self.clients]
        return round(sum(pings) / len(pings), 2)

    async def decorators(self, client: PyTgCalls) -> None:
        participant_update = getattr(types, "UpdatedGroupCallParticipant", None)

        @client.on_update()
        async def update_handler(_, update: types.Update) -> None:
            if isinstance(update, types.StreamEnded):
                if update.stream_type == types.StreamEnded.Type.AUDIO:
                    await self.play_next(update.chat_id)
            elif isinstance(update, types.ChatUpdate):
                if update.status in [
                    types.ChatUpdate.Status.KICKED,
                    types.ChatUpdate.Status.LEFT_GROUP,
                    types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                ]:
                    await self.stop(update.chat_id)
            elif participant_update and isinstance(update, participant_update):
                try:
                    if not await db.get_vc_logger(update.chat_id):
                        return
                    action = getattr(update, "action", None)
                    if action is None:
                        action = getattr(update.participant, "action", None)
                    user_id = getattr(update.participant, "user_id", None)
                    if user_id is None:
                        user_id = getattr(update, "user_id", None)
                    if action == types.GroupCallParticipant.Action.JOINED:
                        await vclogger.notify_join(update.chat_id, user_id)
                    elif action == types.GroupCallParticipant.Action.LEFT:
                        await vclogger.notify_leave(update.chat_id, user_id)
                except Exception:
                    pass

    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("PyTgCalls client(s) started.")
