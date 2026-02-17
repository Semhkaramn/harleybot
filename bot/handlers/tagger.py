import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserNotParticipant
from bot.database.members import (
    save_members_bulk, get_all_members, get_members_count,
    get_members_batch, delete_all_members
)
from bot.database.settings import (
    start_tag_session, get_tag_session, update_tag_index, stop_tag_session
)
from bot.utils.helpers import is_admin, get_user_mention

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

# /kaydet - Save all group members to database
@Client.on_message(filters.command("kaydet") & filters.group)
async def save_all_members(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    status_msg = await message.reply("Uyeler kaydediliyor...")

    members_list = []
    try:
        async for member in client.get_chat_members(chat_id):
            if member.user and not member.user.is_bot:
                members_list.append({
                    'user_id': member.user.id,
                    'username': member.user.username,
                    'first_name': member.user.first_name
                })
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        await status_msg.edit(f"Hata olustu: {str(e)}")
        return

    if members_list:
        await save_members_bulk(chat_id, members_list)
        await status_msg.edit(f"**{len(members_list)}** uye kaydedildi!")
    else:
        await status_msg.edit("Kayit edilecek uye bulunamadi.")

# /üyeler - Show saved members count
@Client.on_message(filters.command(["uyeler", "üyeler"]) & filters.group)
async def show_members_count(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    count = await get_members_count(chat_id)
    await message.reply(f"Kayitli uye sayisi: **{count}**")

# /temizle - Delete all saved members
@Client.on_message(filters.command("temizle") & filters.group)
async def clear_members(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    count = await delete_all_members(chat_id)
    await message.reply(f"**{count}** uye kaydi silindi.")

# /naber - Tag all members with random questions (one message per person)
@Client.on_message(filters.command("naber") & filters.group)
async def naber_tag(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
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

    import random
    for member in members:
        try:
            mention = get_user_mention(member['user_id'], member.get('username'), member.get('first_name'))
            question = random.choice(RANDOM_QUESTIONS)
            await client.send_message(chat_id, f"{mention} {question}")
            await asyncio.sleep(1)  # Anti-flood
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            continue

    await client.send_message(chat_id, "Etiketleme tamamlandi!")

# /etiket <mesaj> - Start tagging 5 people at a time with custom message
@Client.on_message(filters.command("etiket") & filters.group)
async def start_tagging(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    args = message.text.split(None, 1)

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
            await client.send_message(chat_id, "Etiketleme durduruldu.")
            return

        batch = members[index:index + 5]
        mentions = []
        for member in batch:
            mention = get_user_mention(member['user_id'], member.get('username'), member.get('first_name'))
            mentions.append(mention)

        try:
            text = f"{custom_message}\n\n" + " ".join(mentions)
            await client.send_message(chat_id, text)
            index += 5
            await update_tag_index(chat_id, index)
            await asyncio.sleep(3)  # Anti-flood
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Tag error: {e}")
            continue

    await stop_tag_session(chat_id)
    await client.send_message(chat_id, f"Etiketleme tamamlandi! **{total}** kisi etiketlendi.")

# /durdur - Stop ongoing tagging
@Client.on_message(filters.command("durdur") & filters.group)
async def stop_tagging(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
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
@Client.on_message(filters.command("herkes") & filters.group)
async def tag_everyone(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    args = message.text.split(None, 1)
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
                text = f"**{custom_message}**\n\n" + " ".join(mentions)
            else:
                text = " ".join(mentions)
            await client.send_message(chat_id, text)
            await asyncio.sleep(2)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            continue
