import re
from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command

from bot.database.filters import (
    add_filter, get_filter, get_all_filters,
    delete_filter, delete_all_filters, check_filters
)
from bot.utils.helpers import (
    is_admin, process_filter_response, parse_buttons,
    build_keyboard, apply_fillings, parse_random_content
)
from bot.config import ALLOWED_GROUP_ID

router = Router()


def is_allowed_group(chat_id: int) -> bool:
    """Check if bot is allowed to operate in this group"""
    if ALLOWED_GROUP_ID is None:
        return True  # No restriction if not configured
    return chat_id == ALLOWED_GROUP_ID


def parse_filter_keywords(text: str) -> list:
    """Parse filter keywords from command text"""
    keywords = []

    # Check for multiple keywords with parentheses
    paren_match = re.search(r'\(([^)]+)\)', text)
    if paren_match:
        content = paren_match.group(1)
        quoted = re.findall(r'"([^"]+)"', content)
        keywords.extend(quoted)
        remaining = re.sub(r'"[^"]+"', '', content)
        for part in remaining.split(','):
            part = part.strip()
            if part:
                keywords.append(part)
        return keywords

    # Check for quoted phrase
    quoted_match = re.search(r'"([^"]+)"', text)
    if quoted_match:
        return [quoted_match.group(1)]

    # Single word
    parts = text.split(None, 2)
    if len(parts) >= 2:
        keyword = parts[1]
        return [keyword]

    return []


def get_response_text(text: str, keywords: list) -> str:
    """Extract response text from command"""
    parts = text.split(None, 1)
    if len(parts) < 2:
        return ""

    remaining = parts[1]
    remaining = re.sub(r'\([^)]+\)\s*', '', remaining)
    remaining = re.sub(r'"[^"]+"\s*', '', remaining)

    if not re.search(r'[\(\"]', parts[1]):
        parts2 = remaining.split(None, 1)
        if len(parts2) >= 2:
            return parts2[1]
        return ""

    return remaining.strip()


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

    text = message.text or ""
    keywords = parse_filter_keywords(text)
    response = get_response_text(text, keywords)

    media_type = None
    file_id = None
    caption = None
    buttons_list = None

    # Check if replying to a message
    if message.reply_to_message:
        reply = message.reply_to_message
        media_type, file_id = extract_media_info(reply)

        if reply.caption:
            caption = reply.caption
            _, btn_list = parse_buttons(caption)
            if btn_list:
                buttons_list = btn_list
        elif reply.text and not response:
            response = reply.text
            _, btn_list = parse_buttons(response)
            if btn_list:
                buttons_list = btn_list

    if response:
        _, btn_list = parse_buttons(response)
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
            "Bir sticker/resme yanit vererek `/filter kelime`"
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

    if len(added) == 1:
        filter_info = f"**{added[0]}**"
        if media_type:
            filter_info += f" ({media_type})"
        await message.reply(f"Filter eklendi: {filter_info}")
    else:
        await message.reply(f"**{len(added)}** filter eklendi:\n" + ", ".join(f"`{k}`" for k in added))


@router.message(Command("filters"))
async def list_filters(message: Message, bot: Bot):
    if message.chat.type == "private":
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

    all_filters = await get_all_filters(chat_id)

    if not all_filters:
        await message.reply("Bu grupta hic filter yok.")
        return

    text = "**Bu Gruptaki Filterler:**\n\n"
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
    if message.chat.type == "private":
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

    if await delete_filter(chat_id, keyword):
        await message.reply(f"Filter silindi: **{keyword}**")
    else:
        await message.reply(f"Filter bulunamadi: **{keyword}**")


@router.message(Command("stopall"))
async def stop_all_filters(message: Message, bot: Bot):
    if message.chat.type == "private":
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

    count = await delete_all_filters(chat_id)
    await message.reply(f"**{count}** filter silindi.")


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
