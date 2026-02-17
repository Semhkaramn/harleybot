from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from bot.config import BOT_NAME, BOT_VERSION, ALLOWED_GROUP_ID
from bot.utils.helpers import is_admin

router = Router()


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
                    await message.reply(
                        f"**{chat.title}** grubuna baglandiniz!\n\n"
                        "Buradan grup ayarlarini yonetebilirsiniz.\n"
                        "Komutlar icin /help yazin."
                    )
                else:
                    await message.reply("Bu grupta admin degilsiniz!")
            except:
                await message.reply("Gecersiz grup!")
            return

        # Normal start message
        text = (
            f"**Merhaba {user.first_name}!**\n\n"
            f"Ben **{BOT_NAME}** - Grup yonetim botuyum.\n\n"
            "**Ozelliklerim:**\n"
            "- Filter sistemi (resimli, butonlu, formatli)\n"
            "- Etiketleme sistemi\n"
            "- Grup kilitleme\n"
            "- Ban/Mute/Kick komutlari\n"
            "- Pin/Unpin islemleri\n"
            "- Sadece admin komut modu\n\n"
            "Beni bir gruba ekleyip yonetici yapin!"
        )

        me = await bot.get_me()
        buttons = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Gruba Ekle", url=f"https://t.me/{me.username}?startgroup=true"),
                InlineKeyboardButton(text="Yardim", callback_data="help_main")
            ]
        ])

        await message.reply(text, reply_markup=buttons)
    else:
        # Check if allowed group
        if not is_allowed_group(message.chat.id):
            return
        await message.reply(f"**{BOT_NAME}** aktif!\nKomutlar icin: /help")


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
- `/connect` - Ozelden yonetim (sadece gruptan)

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
        await message.reply("Bu komut sadece gruplarda calisir!")
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
                text="Ozelden Devam Et",
                url=f"https://t.me/{me.username}?start=connect_{chat_id}"
            )
        ]
    ])

    await message.reply(
        f"**{chat_title}** grubunu yonetmek icin ozele gelin:",
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

Detayli yardim icin grupta /help yazin.

**Temel Komutlar:**
- /start - Botu baslat
- /help - Yardim
- /connect - Ozelden yonetim
- /id - ID bilgisi
- /info - Kullanici bilgisi
"""

    await callback_query.message.edit_text(text)
