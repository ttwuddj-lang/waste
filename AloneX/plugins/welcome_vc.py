# ALONE-CODER
# Welcome + Voice Chat Logs module

from pyrogram import enums, filters, types
from pyrogram.enums import ButtonStyle
from pyrogram.utils import get_peer_id

from AloneX import anon, app, db, lang, userbot
from AloneX.helpers import admin_check


# The project already contains these premium custom-emoji IDs in en.json.
PREMIUM_SPARKLE = '<emoji id=6269085886177087845>✨</emoji>'
PREMIUM_FIRE = '<emoji id=6086714986309097798>🔥</emoji>'

WELCOME_PHOTO = (
    'https://kommodo.ai/i/eEnbSyk87gV2lAiXwSFx'
)
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


@app.on_message(filters.new_chat_members & filters.group, group=32)
async def welcome_new_members(_, m: types.Message):
    if not await db.get_welcome(m.chat.id):
        return

    for user in m.new_chat_members or []:
        try:
            username = f'@{user.username}' if user.username else 'None'
            caption = (
                '<blockquote>'
                f'{PREMIUM_SPARKLE} <b>𝐖ᴇʟᴄᴏᴍᴇ 𝐓ᴏ Me .</b>\n'
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
            await app.send_photo(
                chat_id=m.chat.id,
                photo=WELCOME_PHOTO,
                caption=caption,
                reply_markup=keyboard,
                quote=True,
            )
        except Exception as exc:
            # If the remote photo URL is rejected, still send the welcome text.
            try:
                await app.send_message(
                    chat_id=m.chat.id,
                    text=caption,
                    reply_markup=keyboard,
                    quote=True,
                )
            except Exception:
                pass


async def _vc_participants_updated(group_call, participants):
    """Send a log when a user actually joins an active voice chat."""
    try:
        chat_id = get_peer_id(group_call.chat_peer)
    except Exception:
        # PyTgCalls exposes chat_peer as a Telegram peer; handle all peer forms.
        peer = getattr(group_call, 'chat_peer', None)
        chat_id = getattr(peer, 'channel_id', None) or getattr(peer, 'chat_id', None) or getattr(peer, 'user_id', None)
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
                    '⌕ 𝐉ᴏɪɴ 𝐕ᴄ',
                    url=join_url,
                    style=ButtonStyle.SUCCESS,
                )
            ]
        ])

    for participant in participants or []:
        if not getattr(participant, 'just_joined', False):
            continue
        if getattr(participant, 'left', False):
            continue

        peer = getattr(participant, 'peer', None)
        user_id = getattr(peer, 'user_id', None)
        if not user_id:
            continue

        # Do not log the music assistants themselves.
        if any(getattr(ub, 'id', None) == user_id for ub in userbot.clients):
            continue

        try:
            user = await app.get_users(user_id)
            auth = await _auth_text(chat_id, user_id)
            text = (
                '<blockquote>'
                f'<b>#JoinedVc</b>\n'
                f'ⓘ 𝖴sᴇʀ - {user.mention}\n'
                f'ⓘ 𝖴sᴇʀɪᴅ - <code>{user.id}</code>\n'
                f'ⓘ 𝖠ᴜᴛʜ - <b>{auth}</b>'
                '</blockquote>'
            )
            await app.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
            )
        except Exception as exc:
            try:
                from AloneX import logger
                logger.exception('VC log handler failed: %s', exc)
            except Exception:
                pass


def register_vc_log_handlers():
    """Register the VC participant callback on every running PyTgCalls client."""
    registered = 0
    for client in getattr(anon, 'clients', []):
        try:
            client.on_participant_list_updated(_vc_participants_updated)
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


register_vc_log_handlers()
