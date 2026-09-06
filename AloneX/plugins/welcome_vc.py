# ALONE-CODER
# Welcome + Voice Chat Logs module

import asyncio

from pyrogram import enums, filters, types
from pyrogram.enums import ButtonStyle
from pyrogram.handlers import ChatMemberUpdatedHandler
from pyrogram.utils import get_peer_id

from AloneX import anon, app, db, lang, userbot
from AloneX.helpers import admin_check


# Premium custom emoji IDs already used by this project.
PREMIUM_SPARKLE = '<emoji id=6269085886177087845>✨</emoji>'
PREMIUM_FIRE = '<emoji id=6086714986309097798>🔥</emoji>'
PREMIUM_HEART = '<emoji id=6113685078825505075>🤍</emoji>'

WELCOME_PHOTO = 'https://kommodo.ai/i/eEnbSyk87gV2lAiXwSFx'
WELCOME_ADD_URL = (
    'http://t.me/Adamusiicbot?startgroup=s&admin='
    'delete_messages+manage_video_chats+pin_messages+invite_users'
)


def _keyboard(rows):
    return types.InlineKeyboardMarkup(rows)


async def _chat_link(chat_id: int) -> str | None:
    try:
        chat = await app.get_chat(chat_id)
        if chat.username:
            return f'https://t.me/{chat.username}'
        if chat.invite_link:
            return chat.invite_link
        try:
            return await app.export_chat_invite_link(chat_id)
        except Exception:
            return None
    except Exception:
        return None


async def _auth_text(chat_id: int, user_id: int) -> str:
    try:
        member = await app.get_chat_member(chat_id, user_id)
        if member.status == enums.ChatMemberStatus.OWNER:
            return 'Owner'
        if member.status == enums.ChatMemberStatus.ADMINISTRATOR:
            return 'Admin'
    except Exception:
        pass
    return 'Member'


async def _delete_after_3s(message: types.Message):
    try:
        await asyncio.sleep(3)
        await message.delete()
    except Exception:
        pass


@app.on_message(
    filters.command(['vclogs']) & filters.group & ~app.bl_users,
    group=30,
)
@lang.language()
@admin_check
async def vc_logs_command(_, m: types.Message):
    if len(m.command) < 2 or m.command[1].lower() not in {'on', 'off'}:
        return await m.reply_text(
            '<b>Usage:</b> <code>/vclogs on</code> or <code>/vclogs off</code>',
            quote=True,
        )

    enabled = m.command[1].lower() == 'on'
    await db.set_vc_logs(m.chat.id, enabled)
    status = 'ON' if enabled else 'OFF'
    await m.reply_text(
        f'{PREMIUM_SPARKLE} <b>VC Logs:</b> <code>{status}</code>',
        quote=True,
    )


@app.on_message(
    filters.command(['welcome']) & filters.group & ~app.bl_users,
    group=31,
)
@lang.language()
@admin_check
async def welcome_command(_, m: types.Message):
    if len(m.command) < 2 or m.command[1].lower() not in {'on', 'off'}:
        return await m.reply_text(
            '<b>Usage:</b> <code>/welcome on</code> or <code>/welcome off</code>',
            quote=True,
        )

    enabled = m.command[1].lower() == 'on'
    await db.set_welcome(m.chat.id, enabled)
    status = 'ON' if enabled else 'OFF'
    await m.reply_text(
        f'{PREMIUM_SPARKLE} <b>Welcome:</b> <code>{status}</code>',
        quote=True,
    )


async def _send_welcome(chat_id: int, user: types.User):
    username = f'@{user.username}' if user.username else 'None'
    caption = (
        '<blockquote>'
        f'{PREMIUM_SPARKLE} <b>𝐖ᴇʟᴄᴏᴍᴇ 𝐓ᴏ Me .</b> {PREMIUM_HEART}{PREMIUM_FIRE}\n'
        f'{PREMIUM_SPARKLE} <b>𝐍ᴀᴍᴇ</b> ✧ {user.mention}\n'
        f'{PREMIUM_SPARKLE} <b>𝐈ᴅ</b> ✧ <code>{user.id}</code>\n'
        f'{PREMIUM_SPARKLE} <b>𝐔sᴇʀɴᴀᴍᴇ</b> ✧ {username}'
        '</blockquote>'
    )
    keyboard = _keyboard([
        [
            types.InlineKeyboardButton(
                '✨ 𝐀ᴅᴅ 𝐌ᴇ',
                url=WELCOME_ADD_URL,
                style=ButtonStyle.SUCCESS,
            )
        ]
    ])

    try:
        return await app.send_photo(
            chat_id=chat_id,
            photo=WELCOME_PHOTO,
            caption=caption,
            reply_markup=keyboard,
        )
    except Exception:
        return await app.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=keyboard,
        )


async def welcome_new_member(_, update: types.ChatMemberUpdated):
    if update.chat.type not in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
        return
    if not update.new_chat_member or not update.new_chat_member.user:
        return

    old_status = getattr(update.old_chat_member, 'status', None)
    new_status = update.new_chat_member.status
    joined_from = {enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED, None}
    joined_to = {
        enums.ChatMemberStatus.MEMBER,
        enums.ChatMemberStatus.RESTRICTED,
        enums.ChatMemberStatus.ADMINISTRATOR,
        enums.ChatMemberStatus.OWNER,
    }
    if old_status not in joined_from or new_status not in joined_to:
        return
    if not await db.get_welcome(update.chat.id):
        return

    user = update.new_chat_member.user
    try:
        msg = await _send_welcome(update.chat.id, user)
        # Welcome remains visible; only VC log/invite messages auto-delete.
        return msg
    except Exception:
        return


# ChatMemberUpdated catches joins even when Telegram's visible service message is hidden.
app.add_handler(ChatMemberUpdatedHandler(welcome_new_member), group=32)


async def _vc_participants_updated(group_call, participants):
    """Send a short-lived VC join log and invite when someone joins the VC."""
    try:
        chat_id = get_peer_id(group_call.chat_peer)
    except Exception:
        peer = getattr(group_call, 'chat_peer', None)
        chat_id = (
            getattr(peer, 'channel_id', None)
            or getattr(peer, 'chat_id', None)
            or getattr(peer, 'user_id', None)
        )
        if chat_id and getattr(peer, 'channel_id', None):
            chat_id = int(f'-100{peer.channel_id}')
        if not chat_id:
            return

    if not await db.get_vc_logs(chat_id):
        return

    join_url = await _chat_link(chat_id)
    keyboard = None
    if join_url:
        keyboard = _keyboard([
            [
                types.InlineKeyboardButton(
                    f'{PREMIUM_SPARKLE} 𝐉ᴏɪɴ 𝐕ᴄ',
                    url=join_url,
                    style=ButtonStyle.SUCCESS,
                )
            ]
        ])

    assistant_ids = {getattr(ub, 'id', None) for ub in userbot.clients}

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
            auth = await _auth_text(chat_id, user_id)

            log_text = (
                '<blockquote>'
                f'{PREMIUM_SPARKLE} <b>#JoinedVc</b> {PREMIUM_FIRE}\n'
                f'ⓘ 𝖴sᴇʀ - {user.mention}\n'
                f'ⓘ 𝖴sᴇʀɪᴅ - <code>{user.id}</code>\n'
                f'ⓘ 𝖠ᴜᴛʜ - <b>{auth}</b>'
                '</blockquote>'
            )
            log_message = await app.send_message(
                chat_id=chat_id,
                text=log_text,
                reply_markup=keyboard,
            )
            asyncio.create_task(_delete_after_3s(log_message))

            invite_text = (
                f'{PREMIUM_SPARKLE} 𝄟𐏓꯭𝄄꯭ ⃪͢ᴍʀ꯭➤ {user.mention} '
                f'❥͜͡≛⃝𝄟{PREMIUM_HEART}{PREMIUM_FIRE}, '
                f'<b>𝐉ᴏɪɴ ᴛʜᴇ 𝐕ᴄ ғᴀsᴛ 😼</b>'
            )
            invite_message = await app.send_message(
                chat_id=chat_id,
                text=invite_text,
                reply_markup=keyboard,
            )
            asyncio.create_task(_delete_after_3s(invite_message))
        except Exception as exc:
            try:
                from AloneX import logger
                logger.exception('VC log handler failed: %s', exc)
            except Exception:
                pass


def register_vc_log_handlers():
    """Register the callback on already-started PyTgCalls clients."""
    registered = 0
    for client in getattr(anon, 'clients', []):
        try:
            # Avoid duplicate registrations if startup calls this more than once.
            if getattr(client, '_alone_vc_log_registered', False):
                continue
            client.on_participant_list_updated(_vc_participants_updated)
            client._alone_vc_log_registered = True
            registered += 1
        except Exception as exc:
            try:
                from AloneX import logger
                logger.exception('Could not register VC log handler: %s', exc)
            except Exception:
                pass

    try:
        from AloneX import logger
        logger.info('VC log handler registered on %s PyTgCalls client(s).', registered)
    except Exception:
        pass
