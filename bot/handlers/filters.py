import re
from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command

from bot.database.filters import (
    add_filter, get_filter, get_all_filters,
    delete_filter, delete_all_filters, check_filters
)
from bot.utils.helpers import (
    is_admin, process_filter_response, parse_buttons, parse_buttons_raw,
    build_keyboard, apply_fillings, parse_random_content
)
from bot.config import ALLOWED_GROUP_ID
from bot.database.settings import get_user_connected_chat

router = Router()


async def get_target_chat(message: Message, bot: Bot) -> tuple:
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


def is_allowed_group(chat_id: int) -> bool:
    """Check if bot is allowed to operate in this group"""
    if ALLOWED_GROUP_ID is None:
        return True  # No restriction if not configured
    return chat_id == ALLOWED_GROUP_ID


def parse_filter_keywords(text: str) -> list:
    """Parse filter keywords from command text"""
    keywords = []

    # Remove /filter command prefix
    if text.startswith('/filter'):
        text = text[7:].strip()

    if not text:
        return []

    # Check for multiple keywords with parentheses at the START only
    # Must not be a button URL (http://, https://, tg://)
    paren_match = re.match(r'^\(([^)]+)\)', text)
    if paren_match:
        content = paren_match.group(1)
        # Make sure it's not a button URL
        if not re.search(r'https?://|tg://|buttonurl:', content.lower()):
            quoted = re.findall(r'"([^"]+)"', content)
            keywords.extend(quoted)
            remaining = re.sub(r'"[^"]+"', '', content)
            for part in remaining.split(','):
                part = part.strip()
                if part:
                    keywords.append(part)
            return keywords

    # Check for quoted phrase at the start
    quoted_match = re.match(r'^"([^"]+)"', text)
    if quoted_match:
        return [quoted_match.group(1)]

    # Single word - first word after /filter is the keyword
    parts = text.split(None, 1)
    if parts:
        keyword = parts[0]
        return [keyword]

    return []


def get_response_text(text: str, keywords: list) -> str:
    """Extract response text from command"""
    # Remove /filter command
    if text.startswith('/filter'):
        text = text[7:].strip()

    if not text:
        return ""

    # Check if starts with keyword group parentheses (not button URL)
    paren_match = re.match(r'^\(([^)]+)\)\s*', text)
    if paren_match and not re.search(r'https?://|tg://|buttonurl:', paren_match.group(1).lower()):
        # Remove the keyword group
        text = text[paren_match.end():].strip()
        return text

    # Check if starts with quoted keyword
    quoted_match = re.match(r'^"[^"]+"\s*', text)
    if quoted_match:
        text = text[quoted_match.end():].strip()
        return text

    # Single word keyword - remove first word
    parts = text.split(None, 1)
    if len(parts) >= 2:
        return parts[1]

    return ""


def extract_media_info(message: Message) -> tuple:
    """Extract media type and file_id from a message"""
    if message.sticker:
        return 'sticker', message.sticker.file_id
    elif message.photo:
        return 'photo', message.photo[-1].file_id
    elif message.animation:
        return 'animation', message.animation.file_id
    elif message.video:
        return 'video', message.video.file_id
    elif message.document:
        return 'document', message.document.file_id
    elif message.audio:
        return 'audio', message.audio.file_id
    elif message.voice:
        return 'voice', message.voice.file_id
    elif message.video_note:
        return 'video_note', message.video_note.file_id
    return None, None


@router.message(Command("filter"))
async def filter_command(message: Message, bot: Bot):
    user_id = message.from_user.id

    # Get target chat (supports private chat connections)
    chat_id, chat_title, is_connected, error = await get_target_chat(message, bot)

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

    # Support both text and caption (for photo/media messages)
    text = message.text or message.caption or ""
    keywords = parse_filter_keywords(text)
    response = get_response_text(text, keywords)

    media_type = None
    file_id = None
    caption = None
    buttons_list = None

    # Check if the command message itself has media
    msg_media_type, msg_file_id = extract_media_info(message)
    if msg_media_type and msg_file_id:
        media_type = msg_media_type
        file_id = msg_file_id

    # Check if replying to a message
    if message.reply_to_message:
        reply = message.reply_to_message
        reply_media_type, reply_file_id = extract_media_info(reply)

        # Use reply media if command message doesn't have media
        if reply_media_type and reply_file_id and not file_id:
            media_type = reply_media_type
            file_id = reply_file_id

        if reply.caption:
            caption = reply.caption
            _, btn_list = parse_buttons_raw(caption)
            if btn_list:
                buttons_list = btn_list
        elif reply.text and not response:
            response = reply.text
            _, btn_list = parse_buttons_raw(response)
            if btn_list:
                buttons_list = btn_list

    if response:
        _, btn_list = parse_buttons_raw(response)
        if btn_list:
            buttons_list = btn_list

    if not keywords:
        await message.reply(
            "**Filter Kullanimi:**\n\n"
            "**Tek kelime:**\n"
            "`/filter merhaba Hos geldin!`\n\n"
            "**Coklu kelime:**\n"
            '`/filter "nasilsin" Iyiyim sen?`\n\n'
            "**Medya ile yanit:**\n"
            "Bir sticker/resme yanit vererek `/filter kelime`\n\n"
            "**Butonlu yanit:**\n"
            "`/filter site Mesaj [Buton](https://link.com)`\n\n"
            "**Yan yana buton (:same):**\n"
            "`[Buton1](https://link1.com) [Buton2](https://link2.com:same)`"
        )
        return

    if not response and not file_id:
        await message.reply("Filter icin bir yanit veya medya belirtin!")
        return

    added = []
    for keyword in keywords:
        filter_type = 'text'
        if media_type:
            filter_type = 'media'
        elif buttons_list:
            filter_type = 'button'

        await add_filter(
            chat_id=chat_id,
            keyword=keyword,
            response=response,
            media_type=media_type,
            file_id=file_id,
            buttons=buttons_list,
            caption=caption,
            filter_type=filter_type
        )
        added.append(keyword)

    # Prepare response message
    group_info = f" (**{chat_title}** grubuna)" if is_connected else ""

    if len(added) == 1:
        filter_info = f"**{added[0]}**"
        if media_type:
            filter_info += f" ({media_type})"
        await message.reply(f"Filter eklendi{group_info}: {filter_info}")
    else:
        await message.reply(f"**{len(added)}** filter eklendi{group_info}:\n" + ", ".join(f"`{k}`" for k in added))


@router.message(Command("filters"))
async def list_filters(message: Message, bot: Bot):
    user_id = message.from_user.id

    # Get target chat (supports private chat connections)
    chat_id, chat_title, is_connected, error = await get_target_chat(message, bot)

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

    all_filters = await get_all_filters(chat_id)

    group_name = chat_title if is_connected else "Bu Grup"

    if not all_filters:
        await message.reply(f"**{group_name}**'ta hic filter yok.")
        return

    text = f"**{group_name} Filterleri:**\n\n"
    for f in all_filters:
        keyword = f['keyword']
        media_type = f.get('media_type')

        type_icon = ""
        if media_type:
            type_icons = {
                'photo': ' [foto]',
                'sticker': ' [sticker]',
                'video': ' [video]',
                'animation': ' [gif]',
                'document': ' [dosya]'
            }
            type_icon = type_icons.get(media_type, ' [medya]')

        text += f"- `{keyword}`{type_icon}\n"

    text += f"\n**Toplam:** {len(all_filters)} filter"
    await message.reply(text)


@router.message(Command("stop"))
async def stop_filter(message: Message, bot: Bot):
    user_id = message.from_user.id

    # Get target chat (supports private chat connections)
    chat_id, chat_title, is_connected, error = await get_target_chat(message, bot)

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

    quoted_match = re.search(r'"([^"]+)"', text)
    if quoted_match:
        keyword = quoted_match.group(1)
    else:
        args = text.split(None, 1)
        if len(args) < 2:
            await message.reply("Silinecek filter kelimesini belirtin:\n`/stop <kelime>`")
            return
        keyword = args[1]

    group_info = f" (**{chat_title}**)" if is_connected else ""

    if await delete_filter(chat_id, keyword):
        await message.reply(f"Filter silindi{group_info}: **{keyword}**")
    else:
        await message.reply(f"Filter bulunamadi{group_info}: **{keyword}**")


@router.message(Command("stopall"))
async def stop_all_filters(message: Message, bot: Bot):
    user_id = message.from_user.id

    # Get target chat (supports private chat connections)
    chat_id, chat_title, is_connected, error = await get_target_chat(message, bot)

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

    group_info = f" (**{chat_title}**)" if is_connected else ""

    count = await delete_all_filters(chat_id)
    await message.reply(f"**{count}** filter silindi{group_info}.")


# Filter checker - responds to messages matching filters
# Only process non-command text messages
@router.message(F.chat.type.in_(["group", "supergroup"]), F.text, ~F.text.startswith("/"))
async def check_filter_message(message: Message, bot: Bot):
    if not message.text:
        return

    chat_id = message.chat.id

    # Check if allowed group
    if not is_allowed_group(chat_id):
        return

    text = message.text
    user = message.from_user
    chat = message.chat

    # Check for matching filter
    filter_data = await check_filters(chat_id, text)

    if not filter_data:
        return

    response = filter_data.get('response')
    media_type = filter_data.get('media_type')
    file_id = filter_data.get('file_id')
    buttons = filter_data.get('buttons')
    caption = filter_data.get('caption')

    # Build keyboard from buttons
    keyboard = None
    if buttons:
        keyboard = build_keyboard(buttons)

    # Process response with fillings, random content, and buttons
    if response:
        processed_response, text_keyboard = process_filter_response(response, user, chat)
        if text_keyboard and not keyboard:
            keyboard = text_keyboard
        response = processed_response

    if caption:
        processed_caption, caption_keyboard = process_filter_response(caption, user, chat)
        if caption_keyboard and not keyboard:
            keyboard = caption_keyboard
        caption = processed_caption

    try:
        if media_type and file_id:
            if media_type == 'sticker':
                await message.reply_sticker(file_id)
            elif media_type == 'photo':
                await message.reply_photo(
                    file_id,
                    caption=caption or response,
                    reply_markup=keyboard
                )
            elif media_type == 'animation':
                await message.reply_animation(
                    file_id,
                    caption=caption or response,
                    reply_markup=keyboard
                )
            elif media_type == 'video':
                await message.reply_video(
                    file_id,
                    caption=caption or response,
                    reply_markup=keyboard
                )
            elif media_type == 'document':
                await message.reply_document(
                    file_id,
                    caption=caption or response,
                    reply_markup=keyboard
                )
            elif media_type == 'audio':
                await message.reply_audio(
                    file_id,
                    caption=caption or response,
                    reply_markup=keyboard
                )
            elif media_type == 'voice':
                await message.reply_voice(file_id, reply_markup=keyboard)
            elif media_type == 'video_note':
                await message.reply_video_note(file_id)
        elif response:
            await message.reply(response, reply_markup=keyboard)
    except Exception:
        pass  # Filter response failed silently
