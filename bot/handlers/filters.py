import re
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.database.filters import (
    add_filter, get_filter, get_all_filters,
    delete_filter, delete_all_filters, check_filters
)
from bot.utils.helpers import is_admin

def parse_filter_keywords(text: str) -> list:
    """Parse filter keywords from command text
    Supports:
    - Single word: /filter hello response
    - Quoted phrase: /filter "hello world" response
    - Multiple: /filter (hi, hello, "hi there") response
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

# /filter <keyword> <response> - Add filter
@Client.on_message(filters.command("filter") & filters.group)
async def filter_command(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
        return

    text = message.text or ""
    keywords = parse_filter_keywords(text)
    response = get_response_text(text, keywords)

    # Check if replying to a message (for media filters)
    if message.reply_to_message and not response:
        # Store the message type for media responses
        reply = message.reply_to_message
        if reply.text:
            response = reply.text
        elif reply.sticker:
            response = f"[sticker:{reply.sticker.file_id}]"
        elif reply.photo:
            response = f"[photo:{reply.photo.file_id}]"
        elif reply.animation:
            response = f"[animation:{reply.animation.file_id}]"
        elif reply.video:
            response = f"[video:{reply.video.file_id}]"
        elif reply.document:
            response = f"[document:{reply.document.file_id}]"

    if not keywords:
        await message.reply(
            "**📝 Filter Kullanımı:**\n\n"
            "**Tek kelime:**\n"
            "`/filter merhaba Hoş geldin!`\n\n"
            "**Çoklu kelime (tırnak ile):**\n"
            "`/filter \"nasılsın\" İyiyim sen?`\n\n"
            "**Birden fazla filter:**\n"
            "`/filter (selam, merhaba, hey) Hoş geldin!`\n\n"
            "**Prefix filter (başlangıç):**\n"
            "`/filter prefix:/yardım Yardım menüsü...`\n\n"
            "**Exact filter (tam eşleşme):**\n"
            "`/filter exact:selam Sadece 'selam' yazınca çalışır`\n\n"
            "**Medya ile yanıt:**\n"
            "Bir sticker/resme yanıt vererek `/filter kelime`"
        )
        return

    if not response:
        await message.reply("❌ Yanıt metni belirtin!")
        return

    added = []
    for keyword in keywords:
        await add_filter(chat_id, keyword, response)
        added.append(keyword)

    if len(added) == 1:
        await message.reply(f"✅ Filter eklendi: **{added[0]}**")
    else:
        await message.reply(f"✅ **{len(added)}** filter eklendi:\n" + ", ".join(f"`{k}`" for k in added))

# /filters - List all filters
@Client.on_message(filters.command("filters") & filters.group)
async def list_filters(client: Client, message: Message):
    chat_id = message.chat.id

    all_filters = await get_all_filters(chat_id)

    if not all_filters:
        await message.reply("📭 Bu grupta hiç filter yok.")
        return

    text = "**📋 Bu Gruptaki Filterler:**\n\n"
    for f in all_filters:
        keyword = f['keyword']
        if keyword.startswith('prefix:'):
            text += f"• `{keyword}` (prefix)\n"
        elif keyword.startswith('exact:'):
            text += f"• `{keyword}` (exact)\n"
        else:
            text += f"• `{keyword}`\n"

    text += f"\n**Toplam:** {len(all_filters)} filter"
    await message.reply(text)

# /stop <keyword> - Delete filter
@Client.on_message(filters.command("stop") & filters.group)
async def stop_filter(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
        return

    text = message.text or ""

    # Check for quoted phrase
    quoted_match = re.search(r'"([^"]+)"', text)
    if quoted_match:
        keyword = quoted_match.group(1)
    else:
        args = text.split(None, 1)
        if len(args) < 2:
            await message.reply("❌ Silinecek filter kelimesini belirtin:\n`/stop <kelime>`\n`/stop \"çoklu kelime\"`")
            return
        keyword = args[1]

    if await delete_filter(chat_id, keyword):
        await message.reply(f"✅ Filter silindi: **{keyword}**")
    else:
        await message.reply(f"❌ Filter bulunamadı: **{keyword}**")

# /stopall - Delete all filters
@Client.on_message(filters.command("stopall") & filters.group)
async def stop_all_filters(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
        return

    count = await delete_all_filters(chat_id)
    await message.reply(f"✅ **{count}** filter silindi.")

# Filter checker - responds to messages matching filters
@Client.on_message(filters.group & filters.text & ~filters.command(["filter", "filters", "stop", "stopall"]))
async def check_filter_message(client: Client, message: Message):
    if not message.text:
        return

    chat_id = message.chat.id
    text = message.text

    # Get all filters for this chat
    all_filters = await get_all_filters(chat_id)

    for f in all_filters:
        keyword = f['keyword']
        response = f['response']
        matched = False

        # Check for exact match
        if keyword.startswith('exact:'):
            trigger = keyword[6:]  # Remove 'exact:' prefix
            if text.lower() == trigger.lower():
                matched = True

        # Check for prefix match
        elif keyword.startswith('prefix:'):
            trigger = keyword[7:]  # Remove 'prefix:' prefix
            if text.lower().startswith(trigger.lower()):
                matched = True

        # Normal match (keyword in message)
        else:
            if keyword.lower() in text.lower():
                matched = True

        if matched:
            # Handle media responses
            if response.startswith('[sticker:'):
                file_id = response[9:-1]
                await message.reply_sticker(file_id)
            elif response.startswith('[photo:'):
                file_id = response[7:-1]
                await message.reply_photo(file_id)
            elif response.startswith('[animation:'):
                file_id = response[11:-1]
                await message.reply_animation(file_id)
            elif response.startswith('[video:'):
                file_id = response[7:-1]
                await message.reply_video(file_id)
            elif response.startswith('[document:'):
                file_id = response[10:-1]
                await message.reply_document(file_id)
            else:
                await message.reply(response)
            return  # Only trigger one filter per message
