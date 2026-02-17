"""
Command Guard Handler
Silently deletes bot commands from non-admin users in groups.
Admin-only command enforcement.
"""

from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command

from bot.utils.helpers import is_admin, is_bot_command
from bot.database.settings import get_chat_settings, set_admin_only_mode, get_user_connected_chat
from bot.config import ALLOWED_GROUP_ID


async def get_target_chat_for_command(message, bot) -> tuple:
    """
    Get target chat_id for commands.
    If in private chat, check for connected group.
    Returns (chat_id, chat_title, is_connected, error_message)
    """
    user_id = message.from_user.id

    if message.chat.type == "private":
        # Check if user is connected to a group
        connection = await get_user_connected_chat(user_id)
        if not connection:
            return None, None, False, (
                "Hicbir gruba bagli degilsiniz!\n\n"
                "Bir gruba baglanmak icin o grupta `/connect` yazin."
            )

        chat_id = connection['chat_id']
        chat_title = connection['chat_title']

        # Verify user is still admin in that group
        if not await is_admin(bot, chat_id, user_id):
            return None, None, False, (
                f"**{chat_title}** grubunda artik admin degilsiniz!\n"
                "Baglanti kesildi."
            )

        return chat_id, chat_title, True, None
    else:
        # In group, use group's chat_id
        return message.chat.id, message.chat.title, False, None

router = Router()


def is_allowed_group(chat_id: int) -> bool:
    """Check if bot is allowed to operate in this group"""
    if ALLOWED_GROUP_ID is None:
        return True  # No restriction if not configured
    return chat_id == ALLOWED_GROUP_ID


# This middleware checks bot commands only
@router.message(F.chat.type.in_(["group", "supergroup"]), F.text.startswith("/"))
async def command_guard(message: Message, bot: Bot):
    """
    Intercept bot commands in groups.
    If it's a bot command from a non-admin:
    - Delete the message silently

    Note: This handler only processes commands (starts with /)
    and does NOT block other handlers from running.
    """
    # Null check for from_user
    if not message.from_user:
        return

    text = message.text.strip()

    # Check if it's one of our bot commands
    if not is_bot_command(text):
        return  # Not our command, let it pass

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if allowed group
    if not is_allowed_group(chat_id):
        # Silently ignore commands in non-allowed groups
        try:
            await message.delete()
        except:
            pass
        # Don't block - let other handlers decide
        return

    # Check if user is admin
    user_is_admin = await is_admin(bot, chat_id, user_id)

    if user_is_admin:
        # Admin can use commands - let the actual command handler process it
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
    if not message.from_user:
        return

    user_id = message.from_user.id

    # Get target chat (supports private chat connections)
    chat_id, chat_title, is_connected, error = await get_target_chat_for_command(message, bot)

    if error:
        await message.reply(error)
        return

    # Check if allowed group
    if not is_allowed_group(chat_id):
        return

    # Check admin in groups (already checked for connected chats)
    if not is_connected and not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    text = message.text or ""
    args = text.split()

    group_info = f" (**{chat_title}**)" if is_connected else ""

    if len(args) < 2:
        settings = await get_chat_settings(chat_id)
        current = settings.get('admin_only_commands', True)
        status = "ACIK" if current else "KAPALI"

        await message.reply(
            f"**Sadece Admin Komutu Modu**{group_info}\n\n"
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
            f"Sadece Admin modu **ACIK**!{group_info}\n\n"
            "Artik sadece adminler bot komutlarini kullanabilir.\n"
            "Diger kullanicilarin komutlari sessizce silinecek."
        )
    elif action in ['off', 'kapali', 'false', '0', 'deaktif']:
        await set_admin_only_mode(chat_id, False)
        await message.reply(
            f"Sadece Admin modu **KAPALI**!{group_info}\n\n"
            "Artik herkes bot komutlarini kullanabilir."
        )
    else:
        await message.reply("Gecersiz secenek. `on` veya `off` kullanin.")
