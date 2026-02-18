import asyncio
from datetime import datetime, timedelta

from aiogram import Router, Bot, F
from aiogram.types import Message, ChatPermissions
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from bot.database.settings import (
    set_chat_locked, save_previous_permissions,
    get_previous_permissions, clear_previous_permissions
)

from bot.utils.helpers import is_admin, can_restrict, get_target_user, get_user_link, extract_time, can_delete
from bot.config import ALLOWED_GROUP_ID

router = Router()


def is_allowed_group(chat_id: int) -> bool:
    """Check if bot is allowed to operate in this group"""
    if ALLOWED_GROUP_ID is None:
        return True  # No restriction if not configured
    return chat_id == ALLOWED_GROUP_ID


# Helper function to check admin and delete if not
async def check_admin_silent(bot: Bot, message: Message) -> bool:
    """Check if user is admin, silently delete if not"""
    # Null check for from_user
    if not message.from_user:
        return False

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if allowed group first
    if not is_allowed_group(chat_id):
        return False

    if not await can_restrict(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return False
    return True

# ==================== BAN COMMANDS ====================

@router.message(Command("ban"))
async def ban_user(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    if not await check_admin_silent(bot, message):
        return

    chat_id = message.chat.id
    target_id, target_name = await get_target_user(bot, message)

    if not target_id:
        await message.reply(
            "**Ban Kullanimi:**\n"
            "- Bir mesajı yanıtlayarak: `/ban`\n"
            "- Kullanici ID ile: `/ban <user_id>`"
        )
        return

    # Check if target is admin
    if await is_admin(bot, chat_id, target_id):
        await message.reply("Adminleri banlayamazsınız!")
        return

    try:
        await bot.ban_chat_member(chat_id, target_id)
        user_link = get_user_link(target_id, target_name)
        await message.reply(f"{user_link} **banlandı!**")
    except TelegramBadRequest as e:
        await message.reply(f"Hata: {e.message}")
    except Exception as e:
        await message.reply(f"Hata: {str(e)}")

@router.message(Command("tban"))
async def tban_user(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    if not await check_admin_silent(bot, message):
        return

    chat_id = message.chat.id
    target_id, target_name = await get_target_user(bot, message)

    if not target_id:
        await message.reply(
            "**Sureli Ban Kullanimi:**\n"
            "`/tban @username 1h` - 1 saat\n"
            "`/tban @username 30m` - 30 dakika\n"
            "`/tban @username 1d` - 1 gun"
        )
        return

    if await is_admin(bot, chat_id, target_id):
        await message.reply("Adminleri banlayamazsınız!")
        return

    # Parse time
    text = message.text or ""
    args = text.split()
    time_str = None

    for arg in args[1:]:
        if arg[0].isdigit() and arg[-1] in 'smhdw':
            time_str = arg
            break

    if not time_str:
        await message.reply("Sure belirtin! Ornek: `/tban @user 1h`")
        return

    duration = extract_time(time_str)
    if not duration:
        await message.reply("Geçersiz sure formati!")
        return

    until_date = datetime.now() + timedelta(seconds=duration)

    try:
        await bot.ban_chat_member(chat_id, target_id, until_date=until_date)
        user_link = get_user_link(target_id, target_name)
        await message.reply(f"{user_link} **{time_str} sureyle banlandı!**")
    except Exception as e:
        await message.reply(f"Hata: {str(e)}")

@router.message(Command("unban"))
async def unban_user(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    if not await check_admin_silent(bot, message):
        return

    chat_id = message.chat.id
    target_id, target_name = await get_target_user(bot, message)

    if not target_id:
        await message.reply("Kullanici belirtin: `/unban user_id`")
        return

    try:
        await bot.unban_chat_member(chat_id, target_id, only_if_banned=True)
        user_link = get_user_link(target_id, target_name)
        await message.reply(f"{user_link} **banı kaldırıldı!**")
    except Exception as e:
        await message.reply(f"Hata: {str(e)}")

# ==================== KICK COMMANDS ====================

@router.message(Command("kick"))
async def kick_user(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    if not await check_admin_silent(bot, message):
        return

    chat_id = message.chat.id
    target_id, target_name = await get_target_user(bot, message)

    if not target_id:
        await message.reply(
            "**Kick Kullanimi:**\n"
            "- `/kick @username`\n"
            "- `/kick user_id`\n"
            "- Mesaji yanıtlayarak: `/kick`"
        )
        return

    if await is_admin(bot, chat_id, target_id):
        await message.reply("Adminleri atamazsiniz!")
        return

    try:
        await bot.ban_chat_member(chat_id, target_id)
        await asyncio.sleep(1)
        await bot.unban_chat_member(chat_id, target_id)
        user_link = get_user_link(target_id, target_name)
        await message.reply(f"{user_link} **atildi!**")
    except Exception as e:
        await message.reply(f"Hata: {str(e)}")

# ==================== MUTE COMMANDS ====================

@router.message(Command("mute"))
async def mute_user(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    if not await check_admin_silent(bot, message):
        return

    chat_id = message.chat.id
    target_id, target_name = await get_target_user(bot, message)

    if not target_id:
        await message.reply(
            "**Mute Kullanimi:**\n"
            "- `/mute @username`\n"
            "- Mesaji yanıtlayarak: `/mute`"
        )
        return

    if await is_admin(bot, chat_id, target_id):
        await message.reply("Adminleri susturamazsiniz!")
        return

    try:
        await bot.restrict_chat_member(
            chat_id,
            target_id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        user_link = get_user_link(target_id, target_name)
        await message.reply(f"{user_link} **susturuldu!**")
    except Exception as e:
        await message.reply(f"Hata: {str(e)}")

@router.message(Command("tmute"))
async def tmute_user(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    if not await check_admin_silent(bot, message):
        return

    chat_id = message.chat.id
    target_id, target_name = await get_target_user(bot, message)

    if not target_id:
        await message.reply(
            "**Sureli Mute Kullanimi:**\n"
            "`/tmute @username 1h` - 1 saat\n"
            "`/tmute @username 30m` - 30 dakika"
        )
        return

    if await is_admin(bot, chat_id, target_id):
        await message.reply("Adminleri susturamazsiniz!")
        return

    text = message.text or ""
    args = text.split()
    time_str = None

    for arg in args[1:]:
        if arg[0].isdigit() and arg[-1] in 'smhdw':
            time_str = arg
            break

    if not time_str:
        await message.reply("Sure belirtin! Ornek: `/tmute @user 1h`")
        return

    duration = extract_time(time_str)
    if not duration:
        await message.reply("Geçersiz sure formati!")
        return

    until_date = datetime.now() + timedelta(seconds=duration)

    try:
        await bot.restrict_chat_member(
            chat_id,
            target_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        user_link = get_user_link(target_id, target_name)
        await message.reply(f"{user_link} **{time_str} sureyle susturuldu!**")
    except Exception as e:
        await message.reply(f"Hata: {str(e)}")

@router.message(Command("unmute"))
async def unmute_user(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    if not await check_admin_silent(bot, message):
        return

    chat_id = message.chat.id
    target_id, target_name = await get_target_user(bot, message)

    if not target_id:
        await message.reply("Kullanici belirtin!")
        return

    try:
        await bot.restrict_chat_member(
            chat_id,
            target_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        user_link = get_user_link(target_id, target_name)
        await message.reply(f"{user_link} **susturması kaldırıldı!**")
    except Exception as e:
        await message.reply(f"Hata: {str(e)}")

# ==================== CHAT KAPAT/AÇ COMMANDS ====================

# Helper function for locking chat
async def _lock_chat(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    if not await check_admin_silent(bot, message):
        return

    chat_id = message.chat.id

    try:
        # Get current chat permissions before locking
        chat = await bot.get_chat(chat_id)
        current_perms = chat.permissions

        if current_perms:
            # Save current permissions to restore later
            perms_to_save = {
                'can_send_messages': current_perms.can_send_messages,
                'can_send_audios': current_perms.can_send_audios,
                'can_send_documents': current_perms.can_send_documents,
                'can_send_photos': current_perms.can_send_photos,
                'can_send_videos': current_perms.can_send_videos,
                'can_send_video_notes': current_perms.can_send_video_notes,
                'can_send_voice_notes': current_perms.can_send_voice_notes,
                'can_send_polls': current_perms.can_send_polls,
                'can_send_other_messages': current_perms.can_send_other_messages,
                'can_add_web_page_previews': current_perms.can_add_web_page_previews,
                'can_change_info': current_perms.can_change_info,
                'can_pin_messages': current_perms.can_pin_messages,
                'can_manage_topics': current_perms.can_manage_topics,
            }
            await save_previous_permissions(chat_id, perms_to_save)

        # Lock chat but ALWAYS keep can_invite_users True
        await bot.set_chat_permissions(
            chat_id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_invite_users=True  # Always keep invite permission open
            )
        )
        await set_chat_locked(chat_id, True)
        await message.reply("**Chat kapatıldı!**")
    except TelegramBadRequest as e:
        await message.reply(f"Hata: {e.message}")


# Helper function for unlocking chat
async def _unlock_chat(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    if not await check_admin_silent(bot, message):
        return

    chat_id = message.chat.id

    try:
        # Get saved previous permissions
        saved_perms = await get_previous_permissions(chat_id)

        if saved_perms:
            # Restore only the permissions that were open before lock
            # Always keep can_invite_users True
            await bot.set_chat_permissions(
                chat_id,
                permissions=ChatPermissions(
                    can_send_messages=saved_perms.get('can_send_messages', True),
                    can_send_audios=saved_perms.get('can_send_audios', True),
                    can_send_documents=saved_perms.get('can_send_documents', True),
                    can_send_photos=saved_perms.get('can_send_photos', True),
                    can_send_videos=saved_perms.get('can_send_videos', True),
                    can_send_video_notes=saved_perms.get('can_send_video_notes', True),
                    can_send_voice_notes=saved_perms.get('can_send_voice_notes', True),
                    can_send_polls=saved_perms.get('can_send_polls', True),
                    can_send_other_messages=saved_perms.get('can_send_other_messages', True),
                    can_add_web_page_previews=saved_perms.get('can_add_web_page_previews', True),
                    can_change_info=saved_perms.get('can_change_info', False),
                    can_pin_messages=saved_perms.get('can_pin_messages', False),
                    can_manage_topics=saved_perms.get('can_manage_topics', False),
                    can_invite_users=True  # Always keep invite permission open
                )
            )
            # Clear saved permissions
            await clear_previous_permissions(chat_id)
        else:
            # No saved permissions, restore all to default
            await bot.set_chat_permissions(
                chat_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_audios=True,
                    can_send_documents=True,
                    can_send_photos=True,
                    can_send_videos=True,
                    can_send_video_notes=True,
                    can_send_voice_notes=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_invite_users=True  # Always keep invite permission open
                )
            )

        await set_chat_locked(chat_id, False)
        await message.reply("**Chat açıldı!**")
    except Exception as e:
        await message.reply(f"Hata: {str(e)}")


# /lock command
@router.message(Command("lock"))
async def lock_chat_cmd(message: Message, bot: Bot):
    await _lock_chat(message, bot)


# /unlock command
@router.message(Command("unlock"))
async def unlock_chat_cmd(message: Message, bot: Bot):
    await _unlock_chat(message, bot)


# "chat kapat" text trigger
@router.message(F.text.casefold() == "chat kapat")
async def lock_chat_text(message: Message, bot: Bot):
    await _lock_chat(message, bot)


# "chat aç" text trigger
@router.message(F.text.casefold() == "chat aç")
async def unlock_chat_text(message: Message, bot: Bot):
    await _unlock_chat(message, bot)

# ==================== MESSAGE MANAGEMENT ====================

@router.message(Command("purge"))
async def purge_messages(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_delete(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    if not message.reply_to_message:
        await message.reply("Silinecek mesajlarin başlangıcını yanıtlayın!")
        return

    start_id = message.reply_to_message.message_id
    end_id = message.message_id

    deleted = 0
    message_ids = list(range(start_id, end_id + 1))

    # Batch delete messages (max 100 per request)
    for i in range(0, len(message_ids), 100):
        batch = message_ids[i:i + 100]
        try:
            await bot.delete_messages(chat_id, batch)
            deleted += len(batch)
        except TelegramBadRequest:
            # Fallback to single deletion if batch fails
            for msg_id in batch:
                try:
                    await bot.delete_message(chat_id, msg_id)
                    deleted += 1
                except Exception:
                    continue
        except Exception:
            continue

    status = await message.answer(f"**{deleted}** mesaj silindi!")
    await asyncio.sleep(3)
    try:
        await status.delete()
    except:
        pass

@router.message(Command("del"))
async def delete_message(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_delete(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    if not message.reply_to_message:
        await message.reply("Silinecek mesajı yanıtlayın!")
        return

    try:
        await message.reply_to_message.delete()
        await message.delete()
    except Exception as e:
        await message.reply(f"Hata: {str(e)}")

# ==================== PIN COMMANDS ====================

@router.message(Command("pin"))
async def pin_message(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    if not message.reply_to_message:
        await message.reply("Sabitlenecek mesajı yanıtlayın!")
        return

    try:
        await bot.pin_chat_message(chat_id, message.reply_to_message.message_id)
        await message.reply("Mesaj sabitlendi!")
    except Exception as e:
        await message.reply(f"Hata: {str(e)}")

@router.message(Command("unpin"))
async def unpin_message(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    try:
        if message.reply_to_message:
            await bot.unpin_chat_message(chat_id, message.reply_to_message.message_id)
        else:
            await bot.unpin_all_chat_messages(chat_id)
        await message.reply("Sabitleme kaldırıldı!")
    except Exception as e:
        await message.reply(f"Hata: {str(e)}")

@router.message(Command("admins"))
async def list_admins(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    text = "**Grup Adminleri:**\n\n"

    try:
        admins = await bot.get_chat_administrators(chat_id)
        for member in admins:
            user = member.user
            if user.is_bot:
                continue

            role = "Kurucu" if member.status == "creator" else "Admin"
            name = user.first_name or "Isimsiz"
            if user.username:
                text += f"{role}: [{name}](https://t.me/{user.username})\n"
            else:
                text += f"{role}: [{name}](tg://user?id={user.id})\n"
    except Exception as e:
        text = f"Hata: {str(e)}"

    await message.reply(text)

# ==================== GIF APPROVAL COMMANDS ====================

@router.message(Command("approve"))
async def approve_gif_user(message: Message, bot: Bot):
    """Approve a user to send GIFs (reply to their message)"""
    if message.chat.type == "private":
        return

    if not message.from_user:
        return

    if not await check_admin_silent(bot, message):
        return

    chat_id = message.chat.id

    # Must reply to a message
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply(
            "**GIF Onay Kullanimi:**\n"
            "Bir kullanicinin mesajini yanitlayarak `/approve` yazin.\n\n"
            "Bu kullaniciya GIF/Sticker atma izni verilecek."
        )
        return

    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    target_name = target_user.first_name or "Kullanici"

    # Don't approve bots
    if target_user.is_bot:
        await message.reply("Botlara izin verilmez!")
        return

    # Check if target is admin (admins don't need approval)
    if await is_admin(bot, chat_id, target_id):
        await message.reply("Adminlerin zaten tum izinleri var!")
        return

    try:
        # Get current user permissions first
        member = await bot.get_chat_member(chat_id, target_id)

        # Build permissions - keep existing, only change can_send_other_messages
        current_perms = {}
        if hasattr(member, 'can_send_messages'):
            current_perms['can_send_messages'] = member.can_send_messages if member.can_send_messages is not None else True
        if hasattr(member, 'can_send_audios'):
            current_perms['can_send_audios'] = member.can_send_audios
        if hasattr(member, 'can_send_documents'):
            current_perms['can_send_documents'] = member.can_send_documents
        if hasattr(member, 'can_send_photos'):
            current_perms['can_send_photos'] = member.can_send_photos
        if hasattr(member, 'can_send_videos'):
            current_perms['can_send_videos'] = member.can_send_videos
        if hasattr(member, 'can_send_video_notes'):
            current_perms['can_send_video_notes'] = member.can_send_video_notes
        if hasattr(member, 'can_send_voice_notes'):
            current_perms['can_send_voice_notes'] = member.can_send_voice_notes
        if hasattr(member, 'can_send_polls'):
            current_perms['can_send_polls'] = member.can_send_polls
        if hasattr(member, 'can_add_web_page_previews'):
            current_perms['can_add_web_page_previews'] = member.can_add_web_page_previews

        # Set can_send_other_messages to True (GIF/Sticker)
        await bot.restrict_chat_member(
            chat_id,
            target_id,
            permissions=ChatPermissions(
                can_send_other_messages=True,
                **current_perms
            )
        )
        user_link = get_user_link(target_id, target_name)
        await message.reply(f"{user_link} artik GIF/Sticker atabilir!")
    except TelegramBadRequest as e:
        await message.reply(f"Hata: {e.message}")
    except Exception as e:
        await message.reply(f"Hata: {str(e)}")


@router.message(Command("disapprove"))
async def disapprove_gif_user(message: Message, bot: Bot):
    """Remove GIF/Sticker permission from a user"""
    if message.chat.type == "private":
        return

    if not message.from_user:
        return

    if not await check_admin_silent(bot, message):
        return

    chat_id = message.chat.id
    target_id, target_name = await get_target_user(bot, message)

    if not target_id:
        await message.reply(
            "**GIF Izni Kaldirma Kullanimi:**\n"
            "- Mesaji yanitlayarak: `/disapprove`\n"
            "- ID ile: `/disapprove <user_id>`"
        )
        return

    # Check if target is admin
    if await is_admin(bot, chat_id, target_id):
        await message.reply("Admin izinleri kaldirilamaz!")
        return

    try:
        # Get current user permissions first
        member = await bot.get_chat_member(chat_id, target_id)

        # Build permissions - keep existing, only change can_send_other_messages
        current_perms = {}
        if hasattr(member, 'can_send_messages'):
            current_perms['can_send_messages'] = member.can_send_messages if member.can_send_messages is not None else True
        if hasattr(member, 'can_send_audios'):
            current_perms['can_send_audios'] = member.can_send_audios
        if hasattr(member, 'can_send_documents'):
            current_perms['can_send_documents'] = member.can_send_documents
        if hasattr(member, 'can_send_photos'):
            current_perms['can_send_photos'] = member.can_send_photos
        if hasattr(member, 'can_send_videos'):
            current_perms['can_send_videos'] = member.can_send_videos
        if hasattr(member, 'can_send_video_notes'):
            current_perms['can_send_video_notes'] = member.can_send_video_notes
        if hasattr(member, 'can_send_voice_notes'):
            current_perms['can_send_voice_notes'] = member.can_send_voice_notes
        if hasattr(member, 'can_send_polls'):
            current_perms['can_send_polls'] = member.can_send_polls
        if hasattr(member, 'can_add_web_page_previews'):
            current_perms['can_add_web_page_previews'] = member.can_add_web_page_previews

        # Set can_send_other_messages to False (no GIF/Sticker)
        await bot.restrict_chat_member(
            chat_id,
            target_id,
            permissions=ChatPermissions(
                can_send_other_messages=False,
                **current_perms
            )
        )
        user_link = get_user_link(target_id, target_name)
        await message.reply(f"{user_link} artik GIF/Sticker atamiyor!")
    except TelegramBadRequest as e:
        await message.reply(f"Hata: {e.message}")
    except Exception as e:
        await message.reply(f"Hata: {str(e)}")
