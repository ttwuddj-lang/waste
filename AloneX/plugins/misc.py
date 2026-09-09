# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic
# ALONE-CODER

import asyncio
import time

from pyrogram import enums, errors, filters, types

from AloneX import anon, app, config, db, lang, logger, queue, tasks, userbot, yt
from AloneX.helpers import buttons


@app.on_message(filters.video_chat_started, group=19)
@app.on_message(filters.video_chat_ended, group=20)
async def _watcher_vc(_, m: types.Message):
    await anon.stop(m.chat.id)


@app.on_chat_join_request()
async def approve_assistants(_, request: types.ChatJoinRequest):
    try:
        assistant_ids = [c.id for c in userbot.clients if hasattr(c, "id")]
        if request.from_user.id in assistant_ids:
            await request.approve()
    except Exception as e:
        logger.error(f"Error approving assistant join request: {e}")


async def auto_leave():
    while True:
        await asyncio.sleep(1800)
        for ub in userbot.clients:
            left = 0
            try:
                for dialog in await ub.get_dialogs():
                    chat_id = dialog.chat.id
                    if left >= 20:
                        break
                    if chat_id in [app.logger, -1001686672798, -1001549206010]:
                        continue
                    if dialog.chat.type in [
                        enums.ChatType.GROUP,
                        enums.ChatType.SUPERGROUP,
                    ]:
                        if chat_id in db.active_calls:
                            continue
                        await ub.leave_chat(chat_id)
                        left += 1
                    await asyncio.sleep(5)
            except:
                continue


async def track_time():
    while True:
        await asyncio.sleep(1)
        for chat_id in list(db.active_calls):
            if not await db.playing(chat_id):
                continue
            media = queue.get_current(chat_id)
            if not media:
                continue
            media.time += 1


async def update_timer(length=10):
    while True:
        await asyncio.sleep(7)
        for chat_id in list(db.active_calls):
            if not await db.playing(chat_id):
                continue
            try:
                media = queue.get_current(chat_id)
                duration, message_id = media.duration_sec, media.message_id
                if not duration or not message_id or not media.time:
                    continue
                played = media.time
                remaining = duration - played
                pos = min(int((played / duration) * length), length - 1)
                timer = "—" * pos + "◉" + "—" * (length - pos - 1)

                if remaining <= 30:
                    next = queue.get_next(chat_id, check=True)
                    if next and not next.file_path:
                        next.file_path = await yt.download(next.id, video=next.video)

                if remaining < 10:
                    remove = True
                else:
                    remove = False
                    timer = f"{time.strftime('%M:%S', time.gmtime(played))} | {timer} | -{time.strftime('%M:%S', time.gmtime(remaining))}"

                await app.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=buttons.controls(
                        chat_id=chat_id, timer=timer, remove=remove
                    ),
                )
            except Exception:
                pass


# Voice-chat participants seen on the previous poll.
vc_seen = {}

async def _participant_id(participant):
    return getattr(participant, "user_id", None) or getattr(participant, "id", None)

async def _participant_mention(participant):
    uid = await _participant_id(participant)
    if not uid:
        return None
    try:
        user = await app.get_users(uid)
        return user.mention
    except Exception:
        return None

async def vc_watcher(sleep=15):
    while True:
        await asyncio.sleep(sleep)
        for chat_id in list(db.active_calls):
            client = await db.get_assistant(chat_id)
            media = queue.get_current(chat_id)
            if not media:
                continue
            try:
                participants = await client.get_participants(chat_id)
                current_ids = set()
                for p in participants:
                    uid = await _participant_id(p)
                    if uid:
                        current_ids.add(uid)

                # Don't announce everyone already present when monitoring starts.
                previous = vc_seen.get(chat_id)
                vc_seen[chat_id] = current_ids

                if config.VC_JOIN_NOTIFY and previous is not None:
                    assistant_ids = {getattr(c, "id", None) for c in userbot.clients}
                    joined = [
                        p for p in participants
                        if (await _participant_id(p)) in (current_ids - previous)
                        and (await _participant_id(p)) not in assistant_ids
                    ]
                    for participant in joined:
                        mention = await _participant_mention(participant)
                        if mention:
                            await app.send_message(
                                chat_id,
                                f"🎙️ <b>{mention}</b> joined the VC!\n🎵 Enjoy the music.",
                            )
            except Exception:
                pass

            if len(participants) < 2 and media.time > 30:
                _lang = await lang.get_lang(chat_id)
                try:
                    sent = await app.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=media.message_id,
                        reply_markup=buttons.controls(
                            chat_id=chat_id, status=_lang["stopped"], remove=True
                        ),
                    )
                    await anon.stop(chat_id)
                    await sent.reply_text(_lang["auto_left"])
                except errors.MessageIdInvalid:
                    pass


if config.AUTO_END or config.VC_JOIN_NOTIFY:
    tasks.append(asyncio.create_task(vc_watcher()))
if config.AUTO_LEAVE:
    tasks.append(asyncio.create_task(auto_leave()))
tasks.append(asyncio.create_task(track_time()))
tasks.append(asyncio.create_task(update_timer()))
