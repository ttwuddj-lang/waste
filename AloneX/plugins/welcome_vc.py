# Welcome + Voice Chat Logs
import asyncio

from pyrogram import enums, filters, types
from pyrogram.enums import ButtonStyle

from AloneX import anon, app, db, lang, userbot
from AloneX.helpers import admin_check

PREMIUM_SPARKLE = '<emoji id=6269085886177087845>✨</emoji>'
PREMIUM_FIRE = '<emoji id=6086714986309097798>🔥</emoji>'
PREMIUM_HEART = '<emoji id=6113685078825505075>🤍</emoji>'

WELCOME_PHOTO = 'https://kommodo.ai/i/eEnbSyk87gV2lAiXwSFx'
WELCOME_ADD_URL = (
    'http://t.me/Adamusiicbot?startgroup=s&admin='
    'delete_messages+manage_video_chats+pin_messages+invite_users'
)


def _keyboard():
    return types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton(
            f'{PREMIUM_SPARKLE} 𝐀ᴅᴅ 𝐌ᴇ',
            url=WELCOME_ADD_URL,
            style=ButtonStyle.SUCCESS,
        )]
    ])


async def _delete_after(message, seconds=3):
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except Exception:
        pass


@app.on_message(filters.command('vclogs') & filters.group & ~app.bl_users, group=30)
@lang.language()
@admin_check
async def vc_logs_command(_, m: types.Message):
    if len(m.command) != 2 or m.command[1].lower() not in ('on', 'off'):
        return await m.reply_text(
            '<b>Usage:</b> <code>/vclogs on</code> / <code>/vclogs off</code>',
            quote=True,
        )
    enabled = m.command[1].lower() == 'on'
    await db.set_vc_logs(m.chat.id, enabled)
    msg = await m.reply_text(
        f'{PREMIUM_SPARKLE} <b>VC Logs:</b> <code>{"ON" if enabled else "OFF"}</code>',
        quote=True,
    )
    asyncio.create_task(_delete_after(msg, 4))


@app.on_message(filters.command('welcome') & filters.group & ~app.bl_users, group=31)
@lang.language()
@admin_check
async def welcome_command(_, m: types.Message):
    if len(m.command) != 2 or m.command[1].lower() not in ('on', 'off'):
        return await m.reply_text(
            '<b>Usage:</b> <code>/welcome on</code> / <code>/welcome off</code>',
            quote=True,
        )
    enabled = m.command[1].lower() == 'on'
    await db.set_welcome(m.chat.id, enabled)
    msg = await m.reply_text(
        f'{PREMIUM_SPARKLE} <b>Welcome:</b> <code>{"ON" if enabled else "OFF"}</code>',
        quote=True,
    )
    asyncio.create_task(_delete_after(msg, 4))


async def _send_welcome(chat_id, user):
    username = f'@{user.username}' if user.username else 'None'
    caption = (
        '<blockquote>'
        f'{PREMIUM_SPARKLE} <b>𝐖ᴇʟᴄᴏᴍᴇ 𝐓ᴏ Me .</b> {PREMIUM_HEART}{PREMIUM_FIRE}\n'
        f'{PREMIUM_SPARKLE} <b>𝐍ᴀᴍᴇ</b> ✧ {user.mention}\n'
        f'{PREMIUM_SPARKLE} <b>𝐈ᴅ</b> ✧ <code>{user.id}</code>\n'
        f'{PREMIUM_SPARKLE} <b>𝐔sᴇʀɴᴀᴍᴇ</b> ✧ {username}'
        '</blockquote>'
    )
    markup = _keyboard()
    try:
        return await app.send_photo(chat_id, WELCOME_PHOTO, caption=caption, reply_markup=markup)
    except Exception:
        return await app.send_message(chat_id, caption, reply_markup=markup)


# Telegram emits this service message when a member is actually added/joined.
# It is considerably more reliable for this bot than manually constructing
# ChatMemberUpdated handlers.
@app.on_message(filters.new_chat_members & filters.group, group=32)
async def welcome_new_member(_, m: types.Message):
    if not await db.get_welcome(m.chat.id):
        return
    for user in (m.new_chat_members or []):
        # Don't welcome the bot itself.
        if user.id == app.id:
            continue
        try:
            await _send_welcome(m.chat.id, user)
        except Exception:
            try:
                from AloneX import logger
                logger.exception('Welcome handler failed in %s', m.chat.id)
            except Exception:
                pass


async def _get_auth(chat_id, user_id):
    try:
        member = await app.get_chat_member(chat_id, user_id)
        if member.status == enums.ChatMemberStatus.OWNER:
            return 'Owner'
        if member.status == enums.ChatMemberStatus.ADMINISTRATOR:
            return 'Admin'
    except Exception:
        pass
    return 'Member'


async def _vc_participants_updated(group_call, participants):
    try:
        chat_id = getattr(group_call, 'chat_peer', None)
        if chat_id is None:
            return
        # PyTgCalls exposes chat_peer as an InputPeer; Pyrogram accepts it
        # through get_peer_id.
        from pyrogram.utils import get_peer_id
        chat_id = get_peer_id(chat_id)
    except Exception:
        return

    if not await db.get_vc_logs(chat_id):
        return

    markup = None
    try:
        chat = await app.get_chat(chat_id)
        invite = chat.invite_link
        if not invite:
            if chat.username:
                invite = f'https://t.me/{chat.username}'
            else:
                invite = await app.export_chat_invite_link(chat_id)
        if invite:
            markup = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(
                f'{PREMIUM_SPARKLE} 𝐉ᴏɪɴ 𝐕ᴄ', url=invite,
                style=ButtonStyle.SUCCESS,
            )]])
    except Exception:
        pass

    assistant_ids = {getattr(x, 'id', None) for x in userbot.clients}
    for participant in participants or []:
        if not getattr(participant, 'just_joined', False):
            continue
        if getattr(participant, 'left', False):
            continue

        peer = getattr(participant, 'peer', None)
        user_id = getattr(peer, 'user_id', None)
        if not user_id or user_id in assistant_ids:
            continue

        try:
            user = await app.get_users(user_id)
            auth = await _get_auth(chat_id, user_id)

            log_text = (
                '<blockquote>'
                f'{PREMIUM_SPARKLE} <b>#JoinedVc</b> {PREMIUM_FIRE}\n'
                f'ⓘ 𝖴sᴇʀ - {user.mention}\n'
                f'ⓘ 𝖴sᴇʀɪᴅ - <code>{user.id}</code>\n'
                f'ⓘ 𝖠ᴜᴛʜ - <b>{auth}</b>'
                '</blockquote>'
            )
            log_msg = await app.send_message(chat_id, log_text, reply_markup=markup)
            asyncio.create_task(_delete_after(log_msg, 3))

            invite_text = (
                f'{PREMIUM_SPARKLE} 𝄟𐏓꯭𝄄꯭ ⃪͢ᴍʀ꯭➤ {user.mention} '
                f'❥͜͡≛⃝𝄟{PREMIUM_HEART}{PREMIUM_FIRE}, '
                '<b>𝐉ᴏɪɴ ᴛʜᴇ 𝐕ᴄ ғᴀsᴛ 😼</b>'
            )
            invite_msg = await app.send_message(chat_id, invite_text, reply_markup=markup)
            asyncio.create_task(_delete_after(invite_msg, 3))
        except Exception:
            try:
                from AloneX import logger
                logger.exception('VC join notification failed for %s', user_id)
            except Exception:
                pass


def register_vc_log_handlers():
    registered = 0
    for client in getattr(anon, 'clients', []):
        try:
            if getattr(client, '_alone_vc_registered', False):
                continue
            client.on_participant_list_updated(_vc_participants_updated)
            client._alone_vc_registered = True
            registered += 1
        except Exception:
            try:
                from AloneX import logger
                logger.exception('VC participant listener registration failed')
            except Exception:
                pass
    try:
        from AloneX import logger
        logger.info('VC participant listener registered: %s', registered)
    except Exception:
        pass
