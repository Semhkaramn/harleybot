"""
Command Guard Handler
Silently deletes bot commands from non-admin users in groups.
Admin-only command enforcement.
"""

from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command

from bot.utils.helpers import is_admin, is_bot_command
from bot.database.settings import get_chat_settings, set_admin_only_mode
from bot.config import ALLOWED_GROUP_ID

router = Router()


def is_allowed_group(chat_id: int) -> bool:
    """Check if bot is allowed to operate in this group"""
    if ALLOWED_GROUP_ID is None:
        return True  # No restriction if not configured
    return chat_id == ALLOWED_GROUP_ID


# This middleware checks all messages
@router.message(F.chat.type.in_(["group", "supergroup"]))
async def command_guard(message: Message, bot: Bot):
    """
    Intercept all text messages in groups.
    If it's a bot command from a non-admin:
    - Delete the message silently
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

    # Check if allowed group
    if not is_allowed_group(chat_id):
        # Silently ignore commands in non-allowed groups
        try:
            await message.delete()
        except:
            pass
        return

    # Check if user is admin
    user_is_admin = await is_admin(bot, chat_id, user_id)

    if user_is_admin:
        # Admin can use commands
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


# /adminonly command
@router.message(Command("adminonly"))
async def toggle_admin_only(message: Message, bot: Bot):
    """Toggle admin-only command mode"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.chat.type == "private":
        await message.reply("Bu komut sadece gruplarda calisir!")
        return

    # Check if allowed group
    if not is_allowed_group(chat_id):
        return

    if not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    text = message.text or ""
    args = text.split()

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
