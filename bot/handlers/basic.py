from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import BOT_NAME, BOT_VERSION

# /start command
@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    user = message.from_user

    if message.chat.type == "private":
        text = (
            f"**Merhaba {user.first_name}!** 👋\n\n"
            f"Ben **{BOT_NAME}** - Rose benzeri grup yönetim botuyum.\n\n"
            "**🔧 Özelliklerim:**\n"
            "• 📝 Filter sistemi (otomatik yanıtlar)\n"
            "• 🏷️ Etiketleme sistemi\n"
            "• 🔒 Grup kilitleme\n"
            "• 🔨 Ban/Mute/Kick komutları\n"
            "• 📌 Pin/Unpin işlemleri\n\n"
            "Beni bir gruba ekleyip yönetici yapın!"
        )

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ Gruba Ekle", url=f"https://t.me/{(await client.get_me()).username}?startgroup=true"),
                InlineKeyboardButton("📚 Yardım", callback_data="help_main")
            ]
        ])

        await message.reply(text, reply_markup=buttons)
    else:
        await message.reply(f"**{BOT_NAME}** aktif! ✅\nKomutlar için: /help")

# /help command
@Client.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    text = f"""
**📚 {BOT_NAME} Komutları**

**🏷️ Etiketleme:**
• `/kaydet` - Üyeleri kaydet
• `/üyeler` - Kayıtlı üye sayısı
• `/temizle` - Kayıtları sil
• `/naber` - Herkese soru sor
• `/etiket <mesaj>` - 5'erli etiketle
• `/durdur` - Etiketlemeyi durdur
• `/herkes <mesaj>` - Herkesi etiketle

**📝 Filter Sistemi:**
• `/filter kelime yanıt` - Filter ekle
• `/filter "çoklu kelime" yanıt` - Çoklu kelime
• `/filter (hi, hello) yanıt` - Birden fazla
• `/filter prefix:/cmd yanıt` - Prefix filter
• `/filter exact:selam yanıt` - Tam eşleşme
• `/filters` - Filterleri listele
• `/stop kelime` - Filter sil
• `/stopall` - Tümünü sil

**🔨 Ban Komutları:**
• `/ban` - Banla
• `/tban <süre>` - Süreli ban (1h, 30m, 1d)
• `/dban` - Mesajı sil + ban
• `/sban` - Sessiz ban
• `/unban` - Ban kaldır

**👢 Kick Komutları:**
• `/kick` - At
• `/dkick` - Mesajı sil + at
• `/skick` - Sessiz at

**🔇 Mute Komutları:**
• `/mute` - Sustur
• `/tmute <süre>` - Süreli sustur
• `/dmute` - Mesajı sil + sustur
• `/smute` - Sessiz sustur
• `/unmute` - Susturmayı kaldır

**🔒 Grup Yönetimi:**
• `/lock` - Grubu kilitle
• `/unlock` - Kilidi aç
• `/del` - Mesaj sil
• `/purge` - Toplu mesaj sil
• `/pin` - Sabitle
• `/unpin` - Sabitlemeyi kaldır
• `/admins` - Admin listesi

**ℹ️ Bilgi:**
• `/id` - ID bilgisi
• `/info` - Kullanıcı bilgisi

**📖 Süre Formatları:**
• `30s` - 30 saniye
• `30m` - 30 dakika
• `1h` - 1 saat
• `1d` - 1 gün
• `1w` - 1 hafta
"""
    await message.reply(text)

# /id command
@Client.on_message(filters.command("id"))
async def id_command(client: Client, message: Message):
    text = ""

    if message.reply_to_message:
        user = message.reply_to_message.from_user
        if user:
            text = (
                f"**👤 Kullanıcı Bilgileri:**\n"
                f"• İsim: {user.first_name}\n"
                f"• ID: `{user.id}`\n"
            )
            if user.username:
                text += f"• Username: @{user.username}\n"
    else:
        user = message.from_user
        text = (
            f"**👤 Senin Bilgilerin:**\n"
            f"• İsim: {user.first_name}\n"
            f"• ID: `{user.id}`\n"
        )
        if user.username:
            text += f"• Username: @{user.username}\n"

    if message.chat.type != "private":
        text += f"\n**💬 Grup ID:** `{message.chat.id}`"

    await message.reply(text)

# /info command
@Client.on_message(filters.command("info"))
async def info_command(client: Client, message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
    else:
        user = message.from_user

    text = f"""
**👤 Kullanıcı Bilgileri**

• **İsim:** {user.first_name}
• **Soyisim:** {user.last_name or "Yok"}
• **Username:** {"@" + user.username if user.username else "Yok"}
• **ID:** `{user.id}`
• **Bot mu:** {"Evet" if user.is_bot else "Hayır"}
• **Premium:** {"Evet" if user.is_premium else "Hayır"}
"""

    await message.reply(text)

# Callback handler for help button
@Client.on_callback_query(filters.regex("^help_main$"))
async def help_callback(client, callback_query):
    await callback_query.answer()
    await help_command(client, callback_query.message)
