from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import BOT_NAME, BOT_VERSION
from bot.utils.helpers import is_admin

# /start command
@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    user = message.from_user

    if message.chat.type == "private":
        text = (
            f"**Merhaba {user.first_name}!**\n\n"
            f"Ben **{BOT_NAME}** - Rose benzeri grup yonetim botuyum.\n\n"
            "**Ozelliklerim:**\n"
            "- Filter sistemi (resimli, butonlu, formatlı)\n"
            "- Etiketleme sistemi\n"
            "- Grup kilitleme\n"
            "- Ban/Mute/Kick komutlari\n"
            "- Pin/Unpin islemleri\n"
            "- Sadece admin komut modu\n\n"
            "Beni bir gruba ekleyip yonetici yapin!"
        )

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Gruba Ekle", url=f"https://t.me/{(await client.get_me()).username}?startgroup=true"),
                InlineKeyboardButton("Yardim", callback_data="help_main")
            ]
        ])

        await message.reply(text, reply_markup=buttons)
    else:
        await message.reply(f"**{BOT_NAME}** aktif!\nKomutlar icin: /help")

# /help command
@Client.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if admin in groups
    if message.chat.type != "private":
        if not await is_admin(client, chat_id, user_id):
            try:
                await message.delete()
            except:
                pass
            return

    text = f"""
**{BOT_NAME} Komutlari**

**Etiketleme:**
- `/kaydet` - Uyeleri kaydet
- `/uyeler` - Kayitli uye sayisi
- `/temizle` - Kayitlari sil
- `/naber` - Herkese soru sor
- `/etiket <mesaj>` - 5'erli etiketle
- `/durdur` - Etiketlemeyi durdur
- `/herkes <mesaj>` - Herkesi etiketle

**Filter Sistemi (Rose tarzı):**
- `/filter kelime yanit` - Filter ekle
- `/filter "coklu kelime" yanit` - Coklu kelime
- `/filter (hi, hello) yanit` - Birden fazla
- `/filter prefix:/cmd yanit` - Prefix filter
- `/filter exact:selam yanit` - Tam eslesme
- `/filters` - Filterleri listele
- `/stop kelime` - Filter sil
- `/stopall` - Tumunu sil

**Filter Ozellikleri:**
- Resim/Sticker/Video/GIF/Dosya destegi
- Butonlu filterler: `[Buton](buttonurl://link.com)`
- Ayni satirda: `[B1](buttonurl://l1:same)`
- Fillings: `{first}`, `{mention}`, `{chatname}` vb.
- Random icerik: `Selam! %%% Merhaba!`

**Ban Komutlari:**
- `/ban` - Banla
- `/tban <sure>` - Sureli ban (1h, 30m, 1d)
- `/dban` - Mesaji sil + ban
- `/sban` - Sessiz ban
- `/unban` - Ban kaldir

**Kick Komutlari:**
- `/kick` - At
- `/dkick` - Mesaji sil + at
- `/skick` - Sessiz at

**Mute Komutlari:**
- `/mute` - Sustur
- `/tmute <sure>` - Sureli sustur
- `/dmute` - Mesaji sil + sustur
- `/smute` - Sessiz sustur
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

**Bilgi:**
- `/id` - ID bilgisi
- `/info` - Kullanici bilgisi

**Sure Formatlari:**
- `30s` - 30 saniye
- `30m` - 30 dakika
- `1h` - 1 saat
- `1d` - 1 gun
- `1w` - 1 hafta
"""
    await message.reply(text)

# /id command
@Client.on_message(filters.command("id"))
async def id_command(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if admin in groups
    if message.chat.type != "private":
        if not await is_admin(client, chat_id, user_id):
            try:
                await message.delete()
            except:
                pass
            return

    text = ""

    if message.reply_to_message:
        user = message.reply_to_message.from_user
        if user:
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
@Client.on_message(filters.command("info"))
async def info_command(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if admin in groups
    if message.chat.type != "private":
        if not await is_admin(client, chat_id, user_id):
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
@Client.on_callback_query(filters.regex("^help_main$"))
async def help_callback(client, callback_query):
    await callback_query.answer()
    await help_command(client, callback_query.message)
