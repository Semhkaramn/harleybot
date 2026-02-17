import asyncio
import random
from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest

from bot.database.members import (
    save_members_bulk, get_all_members, get_members_count,
    get_members_batch, delete_all_members
)
from bot.database.settings import (
    start_tag_session, get_tag_session, update_tag_index, stop_tag_session
)
from bot.utils.helpers import is_admin, get_user_mention
from bot.config import ALLOWED_GROUP_ID

router = Router()

# Random questions for naber tagger
RANDOM_QUESTIONS = [
    "Naber?",
    "Nasilsin?",
    "Ne yapiyorsun?",
    "Iyi misin?",
    "Selam!",
    "Hos geldin!",
    "Burada misin?",
    "Aktif misin?",
    "Gunaydin!",
    "Iyi aksamlar!",
]


def is_allowed_group(chat_id: int) -> bool:
    """Check if bot is allowed to operate in this group"""
    if ALLOWED_GROUP_ID is None:
        return True  # No restriction if not configured
    return chat_id == ALLOWED_GROUP_ID


# /kaydet - Save all group members to database
@router.message(Command("kaydet"))
async def save_all_members(message: Message, bot: Bot):
    if message.chat.type == "private":
        await message.reply("Bu komut sadece gruplarda calisir!")
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if allowed group
    if not is_allowed_group(chat_id):
        return

    if not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    status_msg = await message.reply("Uyeler kaydediliyor...")

    members_list = []
    try:
        # In aiogram, we need to use get_chat_administrators and iterate
        # Note: Bot API doesn't support getting all members, only admins
        # We'll save admins and track members as they send messages
        admins = await bot.get_chat_administrators(chat_id)
        for member in admins:
            if member.user and not member.user.is_bot:
                members_list.append({
                    'user_id': member.user.id,
                    'username': member.user.username,
                    'first_name': member.user.first_name
                })

        # Note: For full member list, you need Telegram Premium API or userbot
        # This implementation saves admins only via Bot API
        # Members will be added as they interact with the bot

    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
    except Exception as e:
        await status_msg.edit_text(f"Hata olustu: {str(e)}")
        return

    if members_list:
        # Don't replace all - merge with existing members
        await save_members_bulk(chat_id, members_list, replace_all=False)
        await status_msg.edit_text(
            f"**{len(members_list)}** admin kaydedildi!\n\n"
            "**Not:** Bot API ile sadece adminler alinabilir.\n"
            "Diger uyeler mesaj attikca otomatik kaydedilir."
        )
    else:
        await status_msg.edit_text("Kayit edilecek uye bulunamadi.")


# /üyeler - Show saved members count
@router.message(Command(commands=["uyeler", "üyeler"]))
async def show_members_count(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_allowed_group(chat_id):
        return

    if not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    count = await get_members_count(chat_id)
    await message.reply(f"Kayitli uye sayisi: **{count}**")


# /temizle - Delete all saved members
@router.message(Command("temizle"))
async def clear_members(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_allowed_group(chat_id):
        return

    if not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    count = await delete_all_members(chat_id)
    await message.reply(f"**{count}** uye kaydi silindi.")


# /naber - Tag all members with random questions (one message per person)
@router.message(Command("naber"))
async def naber_tag(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_allowed_group(chat_id):
        return

    if not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    members = await get_all_members(chat_id)

    if not members:
        await message.reply("Kayitli uye yok! Once `/kaydet` komutunu kullanin.")
        return

    await message.reply(f"**{len(members)}** kisi etiketlenecek...")

    for member in members:
        try:
            mention = get_user_mention(member['user_id'], member.get('username'), member.get('first_name'))
            question = random.choice(RANDOM_QUESTIONS)
            await bot.send_message(chat_id, f"{mention} {question}")
            await asyncio.sleep(1)  # Anti-flood
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception:
            continue

    await bot.send_message(chat_id, "Etiketleme tamamlandi!")


# /etiket <mesaj> - Start tagging 5 people at a time with custom message
@router.message(Command("etiket"))
async def start_tagging(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_allowed_group(chat_id):
        return

    if not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    text = message.text or ""
    args = text.split(None, 1)

    if len(args) < 2:
        await message.reply(
            "**Etiket Kullanimi:**\n\n"
            "`/etiket <mesaj>`\n\n"
            "**Ornek:**\n"
            "`/etiket Bugun saat 20:00'de etkinlik var!`\n\n"
            "Durdurmak icin: `/durdur`"
        )
        return

    custom_message = args[1]

    members = await get_all_members(chat_id)
    if not members:
        await message.reply("Kayitli uye yok! Once `/kaydet` komutunu kullanin.")
        return

    # Start tag session
    await start_tag_session(chat_id, custom_message, user_id)

    await message.reply(f"Etiketleme basladi! **{len(members)}** kisi etiketlenecek (5'er 5'er).\nDurdurmak icin: `/durdur`")

    # Tag 5 people at a time
    total = len(members)
    index = 0

    while index < total:
        # Check if session is still active
        session = await get_tag_session(chat_id)
        if not session or not session['is_active']:
            await bot.send_message(chat_id, "Etiketleme durduruldu.")
            return

        batch = members[index:index + 5]
        mentions = []
        for member in batch:
            mention = get_user_mention(member['user_id'], member.get('username'), member.get('first_name'))
            mentions.append(mention)

        try:
            tag_text = f"{custom_message}\n\n" + " ".join(mentions)
            await bot.send_message(chat_id, tag_text)
            index += 5
            await update_tag_index(chat_id, index)
            await asyncio.sleep(3)  # Anti-flood
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception:
            continue

    await stop_tag_session(chat_id)
    await bot.send_message(chat_id, f"Etiketleme tamamlandi! **{total}** kisi etiketlendi.")


# /durdur - Stop ongoing tagging
@router.message(Command("durdur"))
async def stop_tagging(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_allowed_group(chat_id):
        return

    if not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    session = await get_tag_session(chat_id)
    if session and session['is_active']:
        await stop_tag_session(chat_id)
        await message.reply("Etiketleme durduruldu!")
    else:
        await message.reply("Aktif etiketleme islemi yok.")


# /herkes <mesaj> - Tag everyone at once
@router.message(Command("herkes"))
async def tag_everyone(message: Message, bot: Bot):
    if message.chat.type == "private":
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_allowed_group(chat_id):
        return

    if not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    text = message.text or ""
    args = text.split(None, 1)
    custom_message = args[1] if len(args) > 1 else "Duyuru!"

    members = await get_all_members(chat_id)
    if not members:
        await message.reply("Kayitli uye yok! Once `/kaydet` komutunu kullanin.")
        return

    # Create mention list in chunks of 50 (Telegram limit)
    chunk_size = 50
    for i in range(0, len(members), chunk_size):
        chunk = members[i:i + chunk_size]
        mentions = []
        for member in chunk:
            mention = get_user_mention(member['user_id'], member.get('username'), member.get('first_name'))
            mentions.append(mention)

        try:
            if i == 0:
                tag_text = f"**{custom_message}**\n\n" + " ".join(mentions)
            else:
                tag_text = " ".join(mentions)
            await bot.send_message(chat_id, tag_text)
            await asyncio.sleep(2)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception:
            continue


# Middleware to auto-save member when they send a message
# This runs for every message and doesn't block other handlers
from typing import Callable, Awaitable, Any
from aiogram.types import TelegramObject

@router.message.outer_middleware()
async def auto_save_member_middleware(
    handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
    event: Message,
    data: dict[str, Any]
) -> Any:
    """Middleware to automatically save member info when they send a message"""
    # Only process group messages
    if event.chat.type in ["group", "supergroup"]:
        if event.from_user and not event.from_user.is_bot:
            chat_id = event.chat.id

            if is_allowed_group(chat_id):
                # Import here to avoid circular import
                from bot.database.members import save_member

                try:
                    await save_member(
                        chat_id=chat_id,
                        user_id=event.from_user.id,
                        username=event.from_user.username,
                        first_name=event.from_user.first_name
                    )
                except Exception:
                    pass  # Silently ignore errors

    # Always continue to the next handler
    return await handler(event, data)
