# Welcome + Voice Chat Logs
import asyncio

from pyrogram import enums, filters, types
from pyrogram.enums import ButtonStyle

from AloneX import anon, app, db, lang, userbot, logger
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
async def _welcome_users(chat_id, users):
    if not await db.get_welcome(chat_id):
        return
    for user in users or []:
        if not user or user.id == app.id:
            continue
        try:
            await _send_welcome(chat_id, user)
            from AloneX import logger
            logger.info('Welcome sent for %s in %s', user.id, chat_id)
        except Exception:
            try:
                from AloneX import logger
                logger.exception('Welcome handler failed in %s', chat_id)
            except Exception:
                pass


@app.on_message(filters.new_chat_members & filters.group, group=32)
async def welcome_new_member(_, m: types.Message):
    await _welcome_users(m.chat.id, m.new_chat_members)


@app.on_chat_member_updated(filters.group, group=33)
async def welcome_chat_member(_, update: types.ChatMemberUpdated):
    # Fallback for clients/groups where the service message is not delivered.
    try:
        old = update.old_chat_member
        new = update.new_chat_member
        old_status = getattr(old, 'status', None)
        new_status = getattr(new, 'status', None)
        active = {enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER}
        was_out = old is None or old_status in {enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.RESTRICTED}
        is_in = new_status in active
        if was_out and is_in:
            user = getattr(new, 'user', None)
            await _welcome_users(update.chat.id, [user])
    except Exception:
        try:
            from AloneX import logger
            logger.exception('ChatMember welcome handler failed')
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
    """Handle only fresh VC joins. PyTgCalls sends only changed participants."""
    # PyTgCalls exposes the Telegram chat id on the group-call object in
    # supported versions. Prefer it over raw peer conversion.
    chat_id = getattr(group_call, "chat_id", None)
    if chat_id is None:
        chat_id = getattr(group_call, "_chat_id", None)

    if chat_id is None:
        peer = getattr(group_call, "chat_peer", None)
        if peer is not None:
            try:
                from pyrogram.utils import get_peer_id
                chat_id = get_peer_id(peer)
            except Exception:
                pass

    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        logger.warning("VC join update without a valid chat id: %r", group_call)
        return

    if not await db.get_vc_logs(chat_id):
        return

    # Build a group/VC button when possible. The notification itself is sent
    # even if Telegram does not allow the bot to export an invite link.
    markup = None
    try:
        chat = await app.get_chat(chat_id)
        invite = getattr(chat, "invite_link", None)
        if not invite and getattr(chat, "username", None):
            invite = f"https://t.me/{chat.username}"
        if not invite:
            try:
                invite = await app.export_chat_invite_link(chat_id)
            except Exception:
                invite = None
        if invite:
            markup = types.InlineKeyboardMarkup([[
                types.InlineKeyboardButton(
                    f"{PREMIUM_SPARKLE} 𝐉ᴏɪɴ 𝐕ᴄ",
                    url=invite,
                    style=ButtonStyle.SUCCESS,
                )
            ]])
    except Exception:
        logger.exception("Could not create VC invite button for %s", chat_id)

    assistant_ids = {
        getattr(client, "id", None) for client in getattr(userbot, "clients", [])
    }

    for participant in participants or []:
        try:
            if getattr(participant, "left", False):
                continue
            if not getattr(participant, "just_joined", False):
                continue
            if getattr(participant, "is_self", False):
                continue

            peer = getattr(participant, "peer", None)
            user_id = getattr(peer, "user_id", None)
            if not user_id or user_id in assistant_ids:
                continue

            user = await app.get_users(user_id)
            auth = await _get_auth(chat_id, user_id)

            # 1) Short log notification: delete after exactly ~3 seconds.
            log_text = (
                "<blockquote>"
                f"{PREMIUM_SPARKLE} <b>#JoinedVc</b> {PREMIUM_FIRE}\n"
                f"ⓘ 𝖴sᴇʀ - {user.mention}\n"
                f"ⓘ 𝖴sᴇʀɪᴅ - <code>{user.id}</code>\n"
                f"ⓘ 𝖠ᴜᴛʜ - <b>{auth}</b>"
                "</blockquote>"
            )
            log_msg = await app.send_message(chat_id, log_text)
            asyncio.create_task(_delete_after(log_msg, 3))

            # 2) Separate invite prompt. This is deliberately independent of
            # the button/link creation, so it still appears if export fails.
            invite_text = (
                f"{PREMIUM_SPARKLE} 𝄟𐏓꯭𝄄꯭ ⃪͢ᴍʀ꯭➤ {user.mention} "
                f"❥͜͡≛⃝𝄟{PREMIUM_HEART}{PREMIUM_FIRE}, "
                "<b>𝐉ᴏɪɴ ᴛʜᴇ 𝐕ᴄ ғᴀsᴛ 😼</b>"
            )
            await app.send_message(chat_id, invite_text, reply_markup=markup)

            logger.info("VC join notification + invite sent: user=%s chat=%s", user_id, chat_id)
        except Exception:
            logger.exception("VC join notification failed in chat %s", chat_id)


def register_vc_log_handlers():
    registered = 0
    clients = getattr(anon, "clients", [])
    for client in clients:
        try:
            if getattr(client, "_alone_vc_registered", False):
                registered += 1
                continue
            handler = getattr(client, "on_participant_list_updated", None)
            if not callable(handler):
                logger.error("PyTgCalls client has no participant-list callback API: %r", type(client))
                continue
            handler(_vc_participants_updated)
            client._alone_vc_registered = True
            registered += 1
        except Exception:
            logger.exception("VC participant listener registration failed")
    logger.info("VC participant listener registered: %s/%s", registered, len(clients))
