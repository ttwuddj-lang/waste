from pyrogram import filters, types
from pyrogram.enums import ButtonStyle

from AloneX import app, db, lang
from AloneX.helpers import admin_check

PREMIUM_SPARKLE = '<emoji id=6269085886177087845>✨</emoji>'


@app.on_message(filters.command('autoplay') & filters.group & ~app.bl_users, group=34)
@lang.language()
@admin_check
async def autoplay_command(_, m: types.Message):
    if len(m.command) != 2 or m.command[1].lower() not in ('on', 'off'):
        state = await db.get_autoplay(m.chat.id)
        return await m.reply_text(
            f'{PREMIUM_SPARKLE} <b>Auto Play:</b> <code>{"ON" if state else "OFF"}</code>\n'
            '<blockquote>Use <code>/autoplay on</code> or <code>/autoplay off</code>.</blockquote>',
            quote=True,
        )
    enabled = m.command[1].lower() == 'on'
    await db.set_autoplay(m.chat.id, enabled)
    await m.reply_text(
        f'{PREMIUM_SPARKLE} <b>Auto Play:</b> <code>{"ON ✓" if enabled else "OFF ✕"}</code>',
        quote=True,
    )
