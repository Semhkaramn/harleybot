"""
Command Guard Handler
Silently deletes bot commands from non-admin users in groups.
Admin-only command enforcement.
"""

from pyrogram import Client, filters
from pyrogram.types import Message
from bot.utils.helpers import is_admin, is_bot_command, extract_command_name, BOT_COMMANDS
from bot.database.settings import get_chat_settings


# This handler runs FIRST (group=-1) to intercept commands before other handlers
@Client.on_message(filters.group & filters.text, group=-1)
async def command_guard(client: Client, message: Message):
    """
    Intercept all text messages in groups.
    If it's a bot command from a non-admin:
    - Delete the message silently
    - Don't process further (stop propagation)
    """
    if not message.text:
        return

    text = message.text.strip()

    # Only check messages starting with /
    if not text.startswith('/'):
        return

    # Check if it's one of our bot commands
    if not is_bot_command(text):
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if user is admin
    user_is_admin = await is_admin(client, chat_id, user_id)

    if user_is_admin:
        # Admin can use commands, let the message pass through
        return

    # Non-admin trying to use a bot command
    # Get chat settings to check if admin-only mode is enabled
    settings = await get_chat_settings(chat_id)
    admin_only_enabled = settings.get('admin_only_commands', True)
    delete_enabled = settings.get('delete_non_admin_commands', True)

    if not admin_only_enabled:
        # Admin-only mode is disabled, allow command
        return

    # Delete the message silently
    if delete_enabled:
        try:
            await message.delete()
        except Exception:
            pass

    # Stop propagation - don't let other handlers process this
    message.stop_propagation()


# Settings commands for admins
@Client.on_message(filters.command("adminonly") & filters.group)
async def toggle_admin_only(client: Client, message: Message):
    """Toggle admin-only command mode"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    from bot.database.settings import get_chat_settings

    args = message.text.split()

    if len(args) < 2:
        settings = await get_chat_settings(chat_id)
        current = settings.get('admin_only_commands', True)
        status = "ACIK" if current else "KAPALI"

        await message.reply(
            f"**Sadece Admin Komutu Modu**\n\n"
            f"Mevcut durum: **{status}**\n\n"
            f"Kullanim:\n"
            f"`/adminonly on` - Aktif et (sadece adminler komut kullanabilir)\n"
            f"`/adminonly off` - Deaktif et (herkes komut kullanabilir)"
        )
        return

    action = args[1].lower()

    from bot.database.settings import set_admin_only_mode

    if action in ['on', 'acik', 'true', '1', 'aktif']:
        await set_admin_only_mode(chat_id, True)
        await message.reply(
            "Sadece Admin modu **ACIK**!\n\n"
            "Artik sadece adminler bot komutlarini kullanabilir.\n"
            "Diger kullanicilarin komutlari sessizce silinecek."
        )
    elif action in ['off', 'kapali', 'false', '0', 'deaktif']:
        await set_admin_only_mode(chat_id, False)
        await message.reply(
            "Sadece Admin modu **KAPALI**!\n\n"
            "Artik herkes bot komutlarini kullanabilir."
        )
    else:
        await message.reply("Gecersiz secenek. `on` veya `off` kullanin.")


@Client.on_message(filters.command("setadminonly") & filters.group)
async def set_admin_only_settings(client: Client, message: Message):
    """Configure admin-only settings"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    await message.reply(
        "**Admin Komut Ayarlari**\n\n"
        "`/adminonly on` - Sadece adminler komut kullanabilir\n"
        "`/adminonly off` - Herkes komut kullanabilir\n\n"
        "Bu mod acik oldugunda, admin olmayan kullanicilarin\n"
        "bot komutlari sessizce silinir ve islem yapilmaz."
    )
