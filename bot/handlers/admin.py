import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from pyrogram.errors import FloodWait, UserAdminInvalid, ChatAdminRequired
from bot.database.settings import set_chat_locked, is_chat_locked
from bot.utils.helpers import is_admin, can_restrict, get_target_user, get_user_link, extract_time

# ==================== BAN COMMANDS ====================

# /ban - Ban a user
@Client.on_message(filters.command("ban") & filters.group)
async def ban_user(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
        return

    target_id, target_name = await get_target_user(client, message)

    if not target_id:
        await message.reply(
            "**🔨 Ban Kullanımı:**\n"
            "• Bir mesajı yanıtlayarak: `/ban`\n"
            "• Kullanıcı ID ile: `/ban <user_id>`\n"
            "• Username ile: `/ban @username`\n\n"
            "**Diğer ban komutları:**\n"
            "• `/tban <süre>` - Süreli ban (1h, 30m, 1d)\n"
            "• `/dban` - Mesajı sil + ban\n"
            "• `/sban` - Sessiz ban"
        )
        return

    # Check if target is admin
    if await is_admin(client, chat_id, target_id):
        await message.reply("❌ Adminleri banlayamazsınız!")
        return

    # Get reason if provided
    args = message.text.split()[1:]
    reason = " ".join(args[1:]) if len(args) > 1 else None

    try:
        await client.ban_chat_member(chat_id, target_id)
        user_link = get_user_link(target_id, target_name)
        text = f"🔨 {user_link} **banlandı!**"
        if reason:
            text += f"\n📝 Sebep: {reason}"
        await message.reply(text)
    except UserAdminInvalid:
        await message.reply("❌ Bu kullanıcıyı banlayamıyorum!")
    except ChatAdminRequired:
        await message.reply("❌ Ban yetkisine sahip değilim!")
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# /tban - Temporary ban
@Client.on_message(filters.command("tban") & filters.group)
async def tban_user(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
        return

    target_id, target_name = await get_target_user(client, message)

    if not target_id:
        await message.reply(
            "**⏰ Süreli Ban Kullanımı:**\n"
            "`/tban @username 1h` - 1 saat\n"
            "`/tban @username 30m` - 30 dakika\n"
            "`/tban @username 1d` - 1 gün\n"
            "`/tban @username 1w` - 1 hafta"
        )
        return

    if await is_admin(client, chat_id, target_id):
        await message.reply("❌ Adminleri banlayamazsınız!")
        return

    # Parse time and reason
    args = message.text.split()
    time_str = None
    reason = None

    # Find time argument
    for i, arg in enumerate(args[1:], 1):
        if arg[0].isdigit() and arg[-1] in 'smhdw':
            time_str = arg
            reason = " ".join(args[i+1:]) if len(args) > i+1 else None
            break

    if not time_str:
        await message.reply("❌ Süre belirtin! Örnek: `/tban @user 1h`")
        return

    duration = extract_time(time_str)
    if not duration:
        await message.reply("❌ Geçersiz süre formatı! Örnek: 1h, 30m, 1d")
        return

    until_date = datetime.now() + timedelta(seconds=duration)

    try:
        await client.ban_chat_member(chat_id, target_id, until_date=until_date)
        user_link = get_user_link(target_id, target_name)
        text = f"🔨 {user_link} **{time_str} süreyle banlandı!**"
        if reason:
            text += f"\n📝 Sebep: {reason}"
        await message.reply(text)
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# /dban - Delete message + ban
@Client.on_message(filters.command("dban") & filters.group)
async def dban_user(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
        return

    if not message.reply_to_message:
        await message.reply("❌ `/dban` komutu için bir mesajı yanıtlayın!")
        return

    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.first_name

    if await is_admin(client, chat_id, target_id):
        await message.reply("❌ Adminleri banlayamazsınız!")
        return

    reason = message.text.split(None, 1)[1] if len(message.text.split()) > 1 else None

    try:
        # Delete the message
        await message.reply_to_message.delete()
        # Ban the user
        await client.ban_chat_member(chat_id, target_id)
        user_link = get_user_link(target_id, target_name)
        text = f"🔨 {user_link} **banlandı!** (mesaj silindi)"
        if reason:
            text += f"\n📝 Sebep: {reason}"
        await message.reply(text)
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# /sban - Silent ban (no notification)
@Client.on_message(filters.command("sban") & filters.group)
async def sban_user(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        return  # Silent - no reply

    target_id, target_name = await get_target_user(client, message)

    if not target_id:
        return  # Silent

    if await is_admin(client, chat_id, target_id):
        return  # Silent

    try:
        # Delete replied message if any
        if message.reply_to_message:
            await message.reply_to_message.delete()
        # Delete command message
        await message.delete()
        # Ban the user
        await client.ban_chat_member(chat_id, target_id)
        # No confirmation message (silent)
    except Exception:
        pass

# /unban - Unban a user
@Client.on_message(filters.command("unban") & filters.group)
async def unban_user(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
        return

    target_id, target_name = await get_target_user(client, message)

    if not target_id:
        await message.reply("❌ Kullanıcı belirtin: `/unban @username` veya `/unban user_id`")
        return

    try:
        await client.unban_chat_member(chat_id, target_id)
        user_link = get_user_link(target_id, target_name)
        await message.reply(f"✅ {user_link} **banı kaldırıldı!**")
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# ==================== KICK COMMANDS ====================

# /kick - Kick a user (can rejoin)
@Client.on_message(filters.command("kick") & filters.group)
async def kick_user(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
        return

    target_id, target_name = await get_target_user(client, message)

    if not target_id:
        await message.reply(
            "**👢 Kick Kullanımı:**\n"
            "• `/kick @username`\n"
            "• `/kick user_id`\n"
            "• Mesajı yanıtlayarak: `/kick`\n\n"
            "**Diğer kick komutları:**\n"
            "• `/dkick` - Mesajı sil + kick\n"
            "• `/skick` - Sessiz kick"
        )
        return

    if await is_admin(client, chat_id, target_id):
        await message.reply("❌ Adminleri atamazsınız!")
        return

    reason = " ".join(message.text.split()[2:]) if len(message.text.split()) > 2 else None

    try:
        await client.ban_chat_member(chat_id, target_id)
        await asyncio.sleep(1)
        await client.unban_chat_member(chat_id, target_id)
        user_link = get_user_link(target_id, target_name)
        text = f"👢 {user_link} **atıldı!**"
        if reason:
            text += f"\n📝 Sebep: {reason}"
        await message.reply(text)
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# /dkick - Delete message + kick
@Client.on_message(filters.command("dkick") & filters.group)
async def dkick_user(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
        return

    if not message.reply_to_message:
        await message.reply("❌ `/dkick` komutu için bir mesajı yanıtlayın!")
        return

    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.first_name

    if await is_admin(client, chat_id, target_id):
        await message.reply("❌ Adminleri atamazsınız!")
        return

    reason = message.text.split(None, 1)[1] if len(message.text.split()) > 1 else None

    try:
        await message.reply_to_message.delete()
        await client.ban_chat_member(chat_id, target_id)
        await asyncio.sleep(1)
        await client.unban_chat_member(chat_id, target_id)
        user_link = get_user_link(target_id, target_name)
        text = f"👢 {user_link} **atıldı!** (mesaj silindi)"
        if reason:
            text += f"\n📝 Sebep: {reason}"
        await message.reply(text)
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# /skick - Silent kick
@Client.on_message(filters.command("skick") & filters.group)
async def skick_user(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        return

    target_id, target_name = await get_target_user(client, message)

    if not target_id or await is_admin(client, chat_id, target_id):
        return

    try:
        if message.reply_to_message:
            await message.reply_to_message.delete()
        await message.delete()
        await client.ban_chat_member(chat_id, target_id)
        await asyncio.sleep(1)
        await client.unban_chat_member(chat_id, target_id)
    except Exception:
        pass

# ==================== MUTE COMMANDS ====================

# /mute - Mute a user
@Client.on_message(filters.command("mute") & filters.group)
async def mute_user(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
        return

    target_id, target_name = await get_target_user(client, message)

    if not target_id:
        await message.reply(
            "**🔇 Mute Kullanımı:**\n"
            "• `/mute @username`\n"
            "• Mesajı yanıtlayarak: `/mute`\n\n"
            "**Diğer mute komutları:**\n"
            "• `/tmute <süre>` - Süreli mute (1h, 30m, 1d)\n"
            "• `/dmute` - Mesajı sil + mute\n"
            "• `/smute` - Sessiz mute"
        )
        return

    if await is_admin(client, chat_id, target_id):
        await message.reply("❌ Adminleri susturamazsınız!")
        return

    reason = " ".join(message.text.split()[2:]) if len(message.text.split()) > 2 else None

    try:
        await client.restrict_chat_member(
            chat_id,
            target_id,
            ChatPermissions()  # No permissions
        )
        user_link = get_user_link(target_id, target_name)
        text = f"🔇 {user_link} **susturuldu!**"
        if reason:
            text += f"\n📝 Sebep: {reason}"
        await message.reply(text)
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# /tmute - Temporary mute
@Client.on_message(filters.command("tmute") & filters.group)
async def tmute_user(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
        return

    target_id, target_name = await get_target_user(client, message)

    if not target_id:
        await message.reply(
            "**⏰ Süreli Mute Kullanımı:**\n"
            "`/tmute @username 1h` - 1 saat\n"
            "`/tmute @username 30m` - 30 dakika\n"
            "`/tmute @username 1d` - 1 gün"
        )
        return

    if await is_admin(client, chat_id, target_id):
        await message.reply("❌ Adminleri susturamazsınız!")
        return

    args = message.text.split()
    time_str = None
    reason = None

    for i, arg in enumerate(args[1:], 1):
        if arg[0].isdigit() and arg[-1] in 'smhdw':
            time_str = arg
            reason = " ".join(args[i+1:]) if len(args) > i+1 else None
            break

    if not time_str:
        await message.reply("❌ Süre belirtin! Örnek: `/tmute @user 1h`")
        return

    duration = extract_time(time_str)
    if not duration:
        await message.reply("❌ Geçersiz süre formatı!")
        return

    until_date = datetime.now() + timedelta(seconds=duration)

    try:
        await client.restrict_chat_member(
            chat_id,
            target_id,
            ChatPermissions(),
            until_date=until_date
        )
        user_link = get_user_link(target_id, target_name)
        text = f"🔇 {user_link} **{time_str} süreyle susturuldu!**"
        if reason:
            text += f"\n📝 Sebep: {reason}"
        await message.reply(text)
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# /dmute - Delete message + mute
@Client.on_message(filters.command("dmute") & filters.group)
async def dmute_user(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
        return

    if not message.reply_to_message:
        await message.reply("❌ `/dmute` komutu için bir mesajı yanıtlayın!")
        return

    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.first_name

    if await is_admin(client, chat_id, target_id):
        await message.reply("❌ Adminleri susturamazsınız!")
        return

    reason = message.text.split(None, 1)[1] if len(message.text.split()) > 1 else None

    try:
        await message.reply_to_message.delete()
        await client.restrict_chat_member(chat_id, target_id, ChatPermissions())
        user_link = get_user_link(target_id, target_name)
        text = f"🔇 {user_link} **susturuldu!** (mesaj silindi)"
        if reason:
            text += f"\n📝 Sebep: {reason}"
        await message.reply(text)
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# /smute - Silent mute
@Client.on_message(filters.command("smute") & filters.group)
async def smute_user(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        return

    target_id, target_name = await get_target_user(client, message)

    if not target_id or await is_admin(client, chat_id, target_id):
        return

    try:
        if message.reply_to_message:
            await message.reply_to_message.delete()
        await message.delete()
        await client.restrict_chat_member(chat_id, target_id, ChatPermissions())
    except Exception:
        pass

# /unmute - Unmute a user
@Client.on_message(filters.command("unmute") & filters.group)
async def unmute_user(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
        return

    target_id, target_name = await get_target_user(client, message)

    if not target_id:
        await message.reply("❌ Kullanıcı belirtin!")
        return

    try:
        await client.restrict_chat_member(
            chat_id,
            target_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        user_link = get_user_link(target_id, target_name)
        await message.reply(f"🔊 {user_link} **susturması kaldırıldı!**")
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# ==================== LOCK/UNLOCK COMMANDS ====================

# /lock - Lock the chat (only admins can send messages)
@Client.on_message(filters.command("lock") & filters.group)
async def lock_chat(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
        return

    try:
        await client.set_chat_permissions(
            chat_id,
            ChatPermissions()  # No permissions for regular users
        )
        await set_chat_locked(chat_id, True)
        await message.reply("🔒 **Grup kilitlendi!** Sadece adminler mesaj yazabilir.")
    except ChatAdminRequired:
        await message.reply("❌ Grup kilitleme yetkisine sahip değilim!")
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# /unlock - Unlock the chat
@Client.on_message(filters.command("unlock") & filters.group)
async def unlock_chat(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await can_restrict(client, chat_id, user_id):
        await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
        return

    try:
        await client.set_chat_permissions(
            chat_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_send_polls=True,
                can_add_web_page_previews=True,
                can_invite_users=True
            )
        )
        await set_chat_locked(chat_id, False)
        await message.reply("🔓 **Grup kilidi açıldı!** Herkes mesaj yazabilir.")
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# ==================== MESSAGE MANAGEMENT ====================

# /purge - Delete messages from reply to current
@Client.on_message(filters.command("purge") & filters.group)
async def purge_messages(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    from bot.utils.helpers import can_delete
    if not await can_delete(client, chat_id, user_id):
        await message.reply("❌ Mesaj silme yetkiniz yok!")
        return

    if not message.reply_to_message:
        await message.reply("❌ Silinecek mesajların başlangıcını yanıtlayın!")
        return

    start_id = message.reply_to_message.id
    end_id = message.id

    deleted = 0
    for msg_id in range(start_id, end_id + 1):
        try:
            await client.delete_messages(chat_id, msg_id)
            deleted += 1
        except Exception:
            continue

    status = await message.reply(f"🗑️ **{deleted}** mesaj silindi!")
    await asyncio.sleep(3)
    await status.delete()

# /del - Delete replied message
@Client.on_message(filters.command("del") & filters.group)
async def delete_message(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    from bot.utils.helpers import can_delete
    if not await can_delete(client, chat_id, user_id):
        await message.reply("❌ Mesaj silme yetkiniz yok!")
        return

    if not message.reply_to_message:
        await message.reply("❌ Silinecek mesajı yanıtlayın!")
        return

    try:
        await message.reply_to_message.delete()
        await message.delete()
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# ==================== PIN COMMANDS ====================

# /pin - Pin a message
@Client.on_message(filters.command("pin") & filters.group)
async def pin_message(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
        return

    if not message.reply_to_message:
        await message.reply("❌ Sabitlenecek mesajı yanıtlayın!")
        return

    try:
        await message.reply_to_message.pin()
        await message.reply("📌 Mesaj sabitlendi!")
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# /unpin - Unpin a message
@Client.on_message(filters.command("unpin") & filters.group)
async def unpin_message(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
        return

    try:
        if message.reply_to_message:
            await message.reply_to_message.unpin()
        else:
            await client.unpin_all_chat_messages(chat_id)
        await message.reply("📌 Sabitleme kaldırıldı!")
    except Exception as e:
        await message.reply(f"❌ Hata: {str(e)}")

# /admins - List all admins
@Client.on_message(filters.command("admins") & filters.group)
async def list_admins(client: Client, message: Message):
    chat_id = message.chat.id

    text = "**👮 Grup Adminleri:**\n\n"

    try:
        async for member in client.get_chat_members(chat_id, filter=filters.ChatMembersFilter.ADMINISTRATORS):
            user = member.user
            if user.is_bot:
                continue

            role = "👑 Kurucu" if member.status.name == "OWNER" else "⭐ Admin"
            name = user.first_name or "İsimsiz"
            if user.username:
                text += f"{role}: [{name}](https://t.me/{user.username})\n"
            else:
                text += f"{role}: [{name}](tg://user?id={user.id})\n"
    except Exception as e:
        text = f"❌ Hata: {str(e)}"

    await message.reply(text)
