import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from bot.database.filters import (
    add_filter, get_filter, get_all_filters,
    delete_filter, delete_all_filters, check_filters
)
from bot.utils.helpers import (
    is_admin, process_filter_response, parse_buttons,
    build_keyboard, apply_fillings, parse_random_content
)


def parse_filter_keywords(text: str) -> list:
    """Parse filter keywords from command text
    Supports:
    - Single word: /filter hello response
    - Quoted phrase: /filter "hello world" response
    - Multiple: /filter (hi, hello, "hi there") response
    - Prefix: /filter prefix:/cmd response
    - Exact: /filter exact:hello response
    """
    keywords = []

    # Check for multiple keywords with parentheses: (hi, hello, "hi there")
    paren_match = re.search(r'\(([^)]+)\)', text)
    if paren_match:
        content = paren_match.group(1)
        # Find quoted strings first
        quoted = re.findall(r'"([^"]+)"', content)
        keywords.extend(quoted)
        # Remove quoted strings and split by comma
        remaining = re.sub(r'"[^"]+"', '', content)
        for part in remaining.split(','):
            part = part.strip()
            if part:
                keywords.append(part)
        return keywords

    # Check for quoted phrase: "hello world"
    quoted_match = re.search(r'"([^"]+)"', text)
    if quoted_match:
        return [quoted_match.group(1)]

    # Single word (first word after command)
    parts = text.split(None, 2)
    if len(parts) >= 2:
        keyword = parts[1]
        # Handle prefix: and exact: modifiers
        if keyword.startswith(('prefix:', 'exact:')):
            return [keyword]
        return [keyword]

    return []


def get_response_text(text: str, keywords: list) -> str:
    """Extract response text from command"""
    # Remove command
    parts = text.split(None, 1)
    if len(parts) < 2:
        return ""

    remaining = parts[1]

    # Remove parentheses content
    remaining = re.sub(r'\([^)]+\)\s*', '', remaining)

    # Remove quoted keyword
    remaining = re.sub(r'"[^"]+"\s*', '', remaining)

    # Remove single keyword (first word)
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
        return 'photo', message.photo.file_id
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


# /filter <keyword> <response> - Add filter
@Client.on_message(filters.command("filter") & filters.group)
async def filter_command(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        # Silently delete and ignore for non-admins
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

    # Check if replying to a message (for media filters)
    if message.reply_to_message:
        reply = message.reply_to_message

        # Extract media if present
        media_type, file_id = extract_media_info(reply)

        # Get caption or text
        if reply.caption:
            caption = reply.caption
            # Parse buttons from caption
            _, btn_list = parse_buttons(caption)
            if btn_list:
                buttons_list = btn_list
        elif reply.text and not response:
            response = reply.text
            # Parse buttons from text response
            _, btn_list = parse_buttons(response)
            if btn_list:
                buttons_list = btn_list

    # If response provided in command, parse buttons
    if response:
        _, btn_list = parse_buttons(response)
        if btn_list:
            buttons_list = btn_list

    if not keywords:
        await message.reply(
            "**Filter Kullanimi:**\n\n"
            "**Tek kelime:**\n"
            "`/filter merhaba Hos geldin!`\n\n"
            "**Coklu kelime (tirnak ile):**\n"
            "`/filter \"nasilsin\" Iyiyim sen?`\n\n"
            "**Birden fazla filter:**\n"
            "`/filter (selam, merhaba, hey) Hos geldin!`\n\n"
            "**Prefix filter (baslangic):**\n"
            "`/filter prefix:/yardim Yardim menusu...`\n\n"
            "**Exact filter (tam eslesme):**\n"
            "`/filter exact:selam Sadece 'selam' yazinca calisir`\n\n"
            "**Medya ile yanit:**\n"
            "Bir sticker/resme yanit vererek `/filter kelime`\n\n"
            "**Butonlu filter:**\n"
            "`/filter kelime Mesaj [Buton](buttonurl://link.com)`\n\n"
            "**Ayni satirda butonlar:**\n"
            "`/filter kelime Mesaj [B1](buttonurl://l1.com) [B2](buttonurl://l2.com:same)`\n\n"
            "**Fillings (degiskenler):**\n"
            "`{first}` - Ad\n"
            "`{last}` - Soyad\n"
            "`{fullname}` - Tam isim\n"
            "`{mention}` - Mention\n"
            "`{id}` - Kullanici ID\n"
            "`{chatname}` - Grup adi\n\n"
            "**Random icerik:**\n"
            "`/filter merhaba Selam! %%% Merhaba! %%% Hey!`"
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
        if buttons_list:
            filter_info += " (butonlu)"
        await message.reply(f"Filter eklendi: {filter_info}")
    else:
        await message.reply(f"**{len(added)}** filter eklendi:\n" + ", ".join(f"`{k}`" for k in added))


# /filters - List all filters
@Client.on_message(filters.command("filters") & filters.group)
async def list_filters(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if admin
    if not await is_admin(client, chat_id, user_id):
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
        filter_type = f.get('filter_type', 'text')
        media_type = f.get('media_type')
        buttons = f.get('buttons')

        type_icon = ""
        if media_type:
            type_icons = {
                'photo': ' [foto]',
                'sticker': ' [sticker]',
                'video': ' [video]',
                'animation': ' [gif]',
                'document': ' [dosya]',
                'audio': ' [ses]',
                'voice': ' [sesli mesaj]'
            }
            type_icon = type_icons.get(media_type, ' [medya]')
        elif buttons:
            type_icon = ' [buton]'

        if keyword.startswith('prefix:'):
            text += f"- `{keyword}` (prefix){type_icon}\n"
        elif keyword.startswith('exact:'):
            text += f"- `{keyword}` (exact){type_icon}\n"
        else:
            text += f"- `{keyword}`{type_icon}\n"

    text += f"\n**Toplam:** {len(all_filters)} filter"
    await message.reply(text)


# /stop <keyword> - Delete filter
@Client.on_message(filters.command("stop") & filters.group)
async def stop_filter(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    text = message.text or ""

    # Check for quoted phrase
    quoted_match = re.search(r'"([^"]+)"', text)
    if quoted_match:
        keyword = quoted_match.group(1)
    else:
        args = text.split(None, 1)
        if len(args) < 2:
            await message.reply("Silinecek filter kelimesini belirtin:\n`/stop <kelime>`\n`/stop \"coklu kelime\"`")
            return
        keyword = args[1]

    if await delete_filter(chat_id, keyword):
        await message.reply(f"Filter silindi: **{keyword}**")
    else:
        await message.reply(f"Filter bulunamadi: **{keyword}**")


# /stopall - Delete all filters
@Client.on_message(filters.command("stopall") & filters.group)
async def stop_all_filters(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    count = await delete_all_filters(chat_id)
    await message.reply(f"**{count}** filter silindi.")


# Filter checker - responds to messages matching filters
@Client.on_message(filters.group & filters.text & ~filters.command(["filter", "filters", "stop", "stopall"]), group=5)
async def check_filter_message(client: Client, message: Message):
    if not message.text:
        return

    chat_id = message.chat.id
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

    # Process caption similarly
    if caption:
        processed_caption, caption_keyboard = process_filter_response(caption, user, chat)
        if caption_keyboard and not keyboard:
            keyboard = caption_keyboard
        caption = processed_caption

    try:
        # Send media response
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

        # Send text response
        elif response:
            await message.reply(
                response,
                reply_markup=keyboard,
                disable_web_page_preview='{preview}' not in (filter_data.get('response') or '')
            )
    except Exception as e:
        print(f"Filter response error: {e}")
