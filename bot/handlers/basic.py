from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from typing import Callable, Awaitable, Any
from aiogram.types import TelegramObject

from bot.config import BOT_NAME, BOT_VERSION, ALLOWED_GROUP_ID
from bot.utils.helpers import is_admin
from bot.database.settings import connect_user_to_chat, get_user_connected_chat, disconnect_user

router = Router()


# ==================== SİSTEM MESAJLARINI SİLME ====================

def is_system_message(message: Message) -> bool:
    """Check if a message is a system message (service message)"""
    # Telegram sistem mesajları kontrolü
    service_types = [
        message.new_chat_members,       # Yeni üye katıldı
        message.left_chat_member,       # Üye ayrıldı
        message.pinned_message,         # Mesaj sabitlendi
        message.new_chat_title,         # Grup adı değişti
        message.new_chat_photo,         # Grup fotoğrafı değişti
        message.delete_chat_photo,      # Grup fotoğrafı silindi
        message.group_chat_created,     # Grup oluşturuldu
        message.supergroup_chat_created, # Süper grup oluşturuldu
        message.channel_chat_created,   # Kanal oluşturuldu
        message.message_auto_delete_timer_changed,  # Otomatik silme zamanlayıcısı değişti
        message.migrate_to_chat_id,     # Gruba taşındı
        message.migrate_from_chat_id,   # Gruptan taşındı
        message.video_chat_started,     # Video sohbet başladı
        message.video_chat_ended,       # Video sohbet bitti
        message.video_chat_participants_invited,  # Video sohbet davet edildi
        message.video_chat_scheduled,   # Video sohbet planlandı
        message.forum_topic_created,    # Forum konusu oluşturuldu
        message.forum_topic_edited,     # Forum konusu düzenlendi
        message.forum_topic_closed,     # Forum konusu kapatıldı
        message.forum_topic_reopened,   # Forum konusu yeniden açıldı
        message.general_forum_topic_hidden,    # Genel forum konusu gizlendi
        message.general_forum_topic_unhidden,  # Genel forum konusu gösterildi
        message.write_access_allowed,   # Yazma erişimi verildi
    ]

    # Herhangi biri True/dolu ise sistem mesajıdır
    return any(service_types)


@router.message.outer_middleware()
async def auto_delete_system_messages_middleware(
    handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
    event: Message,
    data: dict[str, Any]
) -> Any:
    """Middleware to automatically delete system/service messages"""
    # Sadece grup mesajlarını işle
    if event.chat.type in ["group", "supergroup"]:
        chat_id = event.chat.id

        # İzin verilen grup kontrolü
        if is_allowed_group(chat_id):
            # Sistem mesajı kontrolü
            if is_system_message(event):
                try:
                    await event.delete()
                except Exception:
                    pass  # Silme hatalarını sessizce geç
                # Sistem mesajını sildikten sonra handler'a devam etmeye gerek yok
                return

    # Normal mesajlar için handler'a devam et
    return await handler(event, data)


def is_allowed_group(chat_id: int) -> bool:
    """Check if bot is allowed to operate in this group"""
    if ALLOWED_GROUP_ID is None:
        return True  # No restriction if not configured
    return chat_id == ALLOWED_GROUP_ID


# /start command
@router.message(Command("start"))
async def start_command(message: Message, bot: Bot):
    user = message.from_user
    text_content = message.text or ""

    if message.chat.type == "private":
        # Handle /start with connect parameter
        if "connect_" in text_content:
            try:
                chat_id = int(text_content.split("connect_")[1])
                chat = await bot.get_chat(chat_id)

                # Verify user is still admin
                if await is_admin(bot, chat_id, message.from_user.id):
                    # Save connection to database
                    await connect_user_to_chat(message.from_user.id, chat_id, chat.title or "Grup")

                    await message.reply(
                        f"**{chat.title}** grubuna bağlandınız!\n\n"
                        "Artik buradan grup ayarlarini yönetebilirsiniz:\n"
                        "- `/filter` - Filter ekle/sil\n"
                        "- `/filters` - Filterleri listele\n"
                        "- `/adminonly` - Admin modu\n"
                        "- `/disconnect` - Baglantıyı kes\n\n"
                        "Diger komutlar için /help yazin."
                    )
                else:
                    await message.reply("Bu grupta admin değilsiniz!")
            except:
                await message.reply("Geçersiz grup!")
            return

        # Normal start message
        text = (
            f"**Merhaba {user.first_name}!**\n\n"
            f"Ben **{BOT_NAME}** - Grup yönetim botuyum.\n\n"
            "**Özelliklerim:**\n"
            "- Filter sistemi (resimli, butonlu, formatli)\n"
            "- Etiketleme sistemi\n"
            "- Grup kilitleme\n"
            "- Ban/Mute/Kick komutları\n"
            "- Pin/Unpin işlemleri\n"
            "- Sadece admin komut modu\n\n"
            "Beni bir gruba ekleyip yönetici yapin!"
        )

        me = await bot.get_me()
        buttons = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Gruba Ekle", url=f"https://t.me/{me.username}?startgroup=true"),
                InlineKeyboardButton(text="Yardım", callback_data="help_main")
            ]
        ])

        await message.reply(text, reply_markup=buttons)
    else:
        # Check if allowed group
        if not is_allowed_group(message.chat.id):
            return
        await message.reply(f"**{BOT_NAME}** aktif!\nKomutlar için: /help")


# /help command
@router.message(Command("help"))
async def help_command(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if admin in groups
    if message.chat.type != "private":
        # Check if allowed group
        if not is_allowed_group(chat_id):
            return

        if not await is_admin(bot, chat_id, user_id):
            try:
                await message.delete()
            except:
                pass
            return

    text = f"""
**{BOT_NAME} Komutlari**

**Baglanti:**
- `/connect` - Özelden yönetim (sadece gruptan)

**Etiketleme:**
- `/kaydet` - Uyeleri kaydet
- `/uyeler` - Kayitli uye sayisi
- `/temizle` - Kayitlari sil
- `/naber` - Herkese soru sor
- `/etiket <mesaj>` - 5'erli etiketle
- `/durdur` - Etiketlemeyi durdur
- `/herkes <mesaj>` - Herkesi etiketle

**Filter Sistemi:**
- `/filter kelime yanit` - Filter ekle
- `/filter "coklu kelime" yanit` - Coklu kelime
- `/filters` - Filterleri listele
- `/stop kelime` - Filter sil
- `/stopall` - Tumunu sil

**Ban Komutlari:**
- `/ban` - Banla
- `/tban <sure>` - Sureli ban (1h, 30m, 1d)
- `/unban` - Ban kaldir

**Kick Komutlari:**
- `/kick` - At

**Mute Komutlari:**
- `/mute` - Sustur
- `/tmute <sure>` - Sureli sustur
- `/unmute` - Susturmayi kaldir

**Grup Yonetimi:**
- `/lock` - Grubu kilitle
- `/unlock` - Kilidi ac
- `/del` - Mesaj sil
- `/purge` - Toplu mesaj sil
- `/pin` - Sabitle
- `/unpin` - Sabitlemeyi kaldir
- `/admins` - Admin listesi

**Admin Modu:**
- `/adminonly on` - Sadece adminler komut kullanabilir
- `/adminonly off` - Herkes komut kullanabilir
"""
    await message.reply(text)


# /connect command - Sends PM button for admin management
@router.message(Command("connect"))
async def connect_command(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Only works in groups
    if message.chat.type == "private":
        await message.reply("Bu komut sadece gruplarda çalışır!")
        return

    # Check if allowed group
    if not is_allowed_group(chat_id):
        return

    # Check if admin
    if not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except:
            pass
        return

    # Admin - send PM button
    me = await bot.get_me()
    chat_title = message.chat.title or "Grup"

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Özelden Devam Et",
                url=f"https://t.me/{me.username}?start=connect_{chat_id}"
            )
        ]
    ])

    await message.reply(
        f"**{chat_title}** grubunu yonetmek için ozele gelin:",
        reply_markup=buttons
    )


# /id command
@router.message(Command("id"))
async def id_command(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if admin in groups
    if message.chat.type != "private":
        # Check if allowed group
        if not is_allowed_group(chat_id):
            return

        if not await is_admin(bot, chat_id, user_id):
            try:
                await message.delete()
            except:
                pass
            return

    text = ""

    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
        text = (
            f"**Kullanici Bilgileri:**\n"
            f"- Isim: {user.first_name}\n"
            f"- ID: `{user.id}`\n"
        )
        if user.username:
            text += f"- Username: @{user.username}\n"
    else:
        user = message.from_user
        text = (
            f"**Senin Bilgilerin:**\n"
            f"- Isim: {user.first_name}\n"
            f"- ID: `{user.id}`\n"
        )
        if user.username:
            text += f"- Username: @{user.username}\n"

    if message.chat.type != "private":
        text += f"\n**Grup ID:** `{message.chat.id}`"

    await message.reply(text)


# /info command
@router.message(Command("info"))
async def info_command(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if admin in groups
    if message.chat.type != "private":
        # Check if allowed group
        if not is_allowed_group(chat_id):
            return

        if not await is_admin(bot, chat_id, user_id):
            try:
                await message.delete()
            except:
                pass
            return

    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
    else:
        user = message.from_user

    text = f"""
**Kullanici Bilgileri**

- **Isim:** {user.first_name}
- **Soyisim:** {user.last_name or "Yok"}
- **Username:** {"@" + user.username if user.username else "Yok"}
- **ID:** `{user.id}`
- **Bot mu:** {"Evet" if user.is_bot else "Hayir"}
- **Premium:** {"Evet" if user.is_premium else "Hayir"}
"""

    await message.reply(text)


# Callback handler for help button
@router.callback_query(F.data == "help_main")
async def help_callback(callback_query: CallbackQuery, bot: Bot):
    await callback_query.answer()

    text = f"""
**{BOT_NAME} Komutlari**

Detayli yardim için grupta /help yazin.

**Temel Komutlar:**
- /start - Botu baslat
- /help - Yardım
- /connect - Özelden yönetim
- /id - ID bilgisi
- /info - Kullanici bilgisi
"""

    await callback_query.message.edit_text(text)


# /disconnect command
@router.message(Command("disconnect"))
async def disconnect_command(message: Message, bot: Bot):
    """Disconnect from connected group"""
    if message.chat.type != "private":
        return

    user_id = message.from_user.id
    connection = await get_user_connected_chat(user_id)

    if not connection:
        await message.reply("Hicbir gruba bagli değilsiniz!")
        return

    await disconnect_user(user_id)
    await message.reply(
        f"**{connection['chat_title']}** grubundan baglanti kesildi!\n\n"
        "Baska bir gruba baglanmak için o grupta `/connect` yazin."
    )


# /status command - show current connection
@router.message(Command("status"))
async def status_command(message: Message, bot: Bot):
    """Show current connection status"""
    if message.chat.type != "private":
        return

    user_id = message.from_user.id
    connection = await get_user_connected_chat(user_id)

    if connection:
        await message.reply(
            f"**Baglanti Durumu**\n\n"
            f"Bagli grup: **{connection['chat_title']}**\n"
            f"Grup ID: `{connection['chat_id']}`\n\n"
            f"Bu gruptan ayri olmak için /disconnect yazin."
        )
    else:
        await message.reply(
            "Hicbir gruba bagli değilsiniz!\n\n"
            "Bir gruba baglanmak için o grupta `/connect` yazin."
        )
