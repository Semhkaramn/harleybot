from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from typing import Callable, Awaitable, Any
from aiogram.types import TelegramObject

from bot.config import BOT_NAME, BOT_VERSION, ALLOWED_GROUP_ID
from bot.utils.helpers import is_admin
from bot.database.settings import connect_user_to_chat, get_user_connected_chat, disconnect_user

router = Router()


# ==================== YARDIMCI FONKSİYONLAR ====================

def is_allowed_group(chat_id: int) -> bool:
    """Check if bot is allowed to operate in this group"""
    if ALLOWED_GROUP_ID is None:
        return True  # No restriction if not configured
    return chat_id == ALLOWED_GROUP_ID


# ==================== HELP MENU KEYBOARDS ====================

def get_help_main_keyboard() -> InlineKeyboardMarkup:
    """Ana yardım menüsü klavyesi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Etiketleme", callback_data="help_tag"),
            InlineKeyboardButton(text="Filter Sistemi", callback_data="help_filter")
        ],
        [
            InlineKeyboardButton(text="Ban/Kick/Mute", callback_data="help_moderation"),
            InlineKeyboardButton(text="Grup Yonetimi", callback_data="help_group")
        ],
        [
            InlineKeyboardButton(text="Baglanti", callback_data="help_connect"),
            InlineKeyboardButton(text="Admin Modu", callback_data="help_admin")
        ],
        [
            InlineKeyboardButton(text="Bilgi Komutlari", callback_data="help_info")
        ]
    ])


def get_back_button() -> InlineKeyboardMarkup:
    """Geri butonu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Geri", callback_data="help_main")]
    ])


# ==================== SİSTEM MESAJLARINI SİLME ====================

def is_system_message(message: Message) -> bool:
    """Check if a message is a system message (service message)"""
    service_types = [
        message.new_chat_members,
        message.left_chat_member,
        message.pinned_message,
        message.new_chat_title,
        message.new_chat_photo,
        message.delete_chat_photo,
        message.group_chat_created,
        message.supergroup_chat_created,
        message.channel_chat_created,
        message.message_auto_delete_timer_changed,
        message.migrate_to_chat_id,
        message.migrate_from_chat_id,
        message.video_chat_started,
        message.video_chat_ended,
        message.video_chat_participants_invited,
        message.video_chat_scheduled,
        message.forum_topic_created,
        message.forum_topic_edited,
        message.forum_topic_closed,
        message.forum_topic_reopened,
        message.general_forum_topic_hidden,
        message.general_forum_topic_unhidden,
        message.write_access_allowed,
    ]
    return any(service_types)


@router.message.outer_middleware()
async def auto_delete_system_messages_middleware(
    handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
    event: Message,
    data: dict[str, Any]
) -> Any:
    """Middleware to automatically delete system/service messages"""
    if event.chat.type in ["group", "supergroup"]:
        chat_id = event.chat.id
        if is_allowed_group(chat_id):
            if is_system_message(event):
                try:
                    await event.delete()
                except Exception:
                    pass
                return
    return await handler(event, data)


# /start command
@router.message(Command("start"))
async def start_command(message: Message, bot: Bot):
    if not message.from_user:
        return

    user = message.from_user
    text_content = message.text or ""

    if message.chat.type == "private":
        # Handle /start with connect parameter
        if "connect_" in text_content:
            try:
                chat_id = int(text_content.split("connect_")[1])
                chat = await bot.get_chat(chat_id)

                if await is_admin(bot, chat_id, message.from_user.id):
                    await connect_user_to_chat(message.from_user.id, chat_id, chat.title or "Grup")

                    await message.reply(
                        f"**{chat.title}** grubuna baglandiniz!\n\n"
                        "Artik buradan grup ayarlarini yonetebilirsiniz:\n"
                        "- `/filter` - Filter ekle/sil\n"
                        "- `/filters` - Filterleri listele\n"
                        "- `/adminonly` - Admin modu\n"
                        "- `/disconnect` - Baglantiyi kes\n\n"
                        "Diger komutlar icin /help yazin."
                    )
                else:
                    await message.reply("Bu grupta admin degilsiniz!")
            except Exception:
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
        if not is_allowed_group(message.chat.id):
            return
        await message.reply(f"**{BOT_NAME}** aktif!\nKomutlar icin: /help")


# /help command
@router.message(Command("help"))
async def help_command(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None

    if not user_id:
        return

    if message.chat.type != "private":
        if not is_allowed_group(chat_id):
            return

        if not await is_admin(bot, chat_id, user_id):
            try:
                await message.delete()
            except Exception:
                pass
            return

    text = f"""
**{BOT_NAME} Yardim Menusu**

Asagidaki butonlara tiklayarak detayli bilgi alabilirsiniz.

**Hizli Bakis:**
- **Etiketleme:** Grup uyelerini etiketleme
- **Filter:** Otomatik yanitlar
- **Moderasyon:** Ban/Kick/Mute islemleri
- **Grup Yonetimi:** Lock/Pin/Purge vs.
- **Baglanti:** Ozelden grup yonetimi
- **Admin Modu:** Komut kisitlamalari

Bir kategori secin:
"""
    await message.reply(text, reply_markup=get_help_main_keyboard())


# ==================== HELP CALLBACK HANDLERS ====================

@router.callback_query(F.data == "help_main")
async def help_main_callback(callback_query: CallbackQuery, bot: Bot):
    """Ana yardım menüsüne dön"""
    await callback_query.answer()

    text = f"""
**{BOT_NAME} Yardim Menusu**

Asagidaki butonlara tiklayarak detayli bilgi alabilirsiniz.

**Hizli Bakis:**
- **Etiketleme:** Grup uyelerini etiketleme
- **Filter:** Otomatik yanitlar
- **Moderasyon:** Ban/Kick/Mute islemleri
- **Grup Yonetimi:** Lock/Pin/Purge vs.
- **Baglanti:** Ozelden grup yonetimi
- **Admin Modu:** Komut kisitlamalari

Bir kategori secin:
"""
    await callback_query.message.edit_text(text, reply_markup=get_help_main_keyboard())


@router.callback_query(F.data == "help_tag")
async def help_tag_callback(callback_query: CallbackQuery, bot: Bot):
    """Etiketleme yardımı"""
    await callback_query.answer()

    text = """
**ETIKETLEME SISTEMI**

Grup uyelerini etiketlemek icin kullanilir.

**Komutlar:**

`/kaydet`
Grup uyelerini veritabanina kaydeder. Ilk olarak adminler kaydedilir, diger uyeler mesaj attikca otomatik eklenir.

`/uyeler` veya `/üyeler`
Kayitli uye sayisini gosterir.

`/temizle`
Tum kayitli uyeleri siler.

`/naber`
Her uyeye tek tek rastgele sorular gonderir:
"Naber?", "Nasilsin?", "Ne yapiyorsun?" gibi.

`/etiket <mesaj>`
5'erli gruplar halinde etiketler.
Ornek: `/etiket Bugun saat 20:00'de toplanti var!`

`/durdur`
Devam eden etiketleme islemini durdurur.

`/herkes <mesaj>`
Tum uyeleri tek seferde etiketler.
Ornek: `/herkes Onemli duyuru!`

**Not:** Uyeler mesaj attikca otomatik kaydedilir.
"""
    await callback_query.message.edit_text(text, reply_markup=get_back_button())


@router.callback_query(F.data == "help_filter")
async def help_filter_callback(callback_query: CallbackQuery, bot: Bot):
    """Filter yardımı"""
    await callback_query.answer()

    text = """
**FILTER SISTEMI**

Belirli kelimelere otomatik yanit verir.

**Komutlar:**

`/filter <kelime> <yanit>`
Yeni filter ekler.
Ornek: `/filter selam Merhaba!`

`/filter "coklu kelime" <yanit>`
Coklu kelime filtreleri icin tirnak kullanin.
Ornek: `/filter "nasilsin" Iyiyim sen?`

`/filters`
Tum filtreleri listeler.

`/stop <kelime>`
Filter siler.
Ornek: `/stop selam`

`/stopall`
Tum filterleri siler.

**Medya ile Filter:**
Bir sticker/resme yanit vererek:
`/filter kelime`

**Butonlu Filter:**
`/filter site Mesaj [Buton](https://link.com)`

**Yan Yana Butonlar (:same):**
`/filter test [Btn1](https://link1.com) [Btn2](https://link2.com:same)`

**Ozel Formatlar:**
- `{first}` - Kullanici adi
- `{username}` - @kullanici
- `{mention}` - Tiklanabilir mention
- `{chatname}` - Grup adi

**Filter Turleri:**
- Normal: Kelime cumle icinde gecerse tetiklenir
- `prefix:kelime` - Mesaj bu kelimeyle baslarsa
- `exact:kelime` - Tam eslesme gerekir
"""
    await callback_query.message.edit_text(text, reply_markup=get_back_button())


@router.callback_query(F.data == "help_moderation")
async def help_moderation_callback(callback_query: CallbackQuery, bot: Bot):
    """Moderasyon yardımı"""
    await callback_query.answer()

    text = """
**MODERASYON KOMUTLARI**

**BAN Komutlari:**

`/ban`
Kullaniciyi kalici olarak banlar.
- Mesaji yanitlayarak: `/ban`
- ID ile: `/ban 123456789`
- Username ile: `/ban @kullanici`

`/tban <sure>`
Sureli ban.
- `/tban @user 1h` - 1 saat
- `/tban @user 30m` - 30 dakika
- `/tban @user 1d` - 1 gun
- `/tban @user 1w` - 1 hafta

`/unban`
Bani kaldirir.

**KICK Komutlari:**

`/kick`
Kullaniciyi gruptan atar (tekrar katilabilir).

**MUTE Komutlari:**

`/mute`
Kullaniciyi susturur (mesaj yazamaz).

`/tmute <sure>`
Sureli susturma.
- `/tmute @user 1h` - 1 saat
- `/tmute @user 30m` - 30 dakika

`/unmute`
Susturmayi kaldirir.

**Not:** Bu komutlar sadece adminler tarafindan kullanilabilir.
"""
    await callback_query.message.edit_text(text, reply_markup=get_back_button())


@router.callback_query(F.data == "help_group")
async def help_group_callback(callback_query: CallbackQuery, bot: Bot):
    """Grup yönetimi yardımı"""
    await callback_query.answer()

    text = """
**GRUP YONETIMI**

**Grup Kilitleme:**

`/lock` veya `chat kapat`
Grubu kilitler - sadece adminler mesaj yazabilir.

`/unlock` veya `chat ac`
Kilidi kaldirir.

**Mesaj Yonetimi:**

`/del`
Yanitlanan mesaji siler.

`/purge`
Yanitlanan mesajdan itibaren tum mesajlari siler.
(Toplu silme islemi)

**Sabitleme:**

`/pin`
Yanitlanan mesaji sabitler.

`/unpin`
- Yanitlanan mesajin sabitlemesini kaldirir.
- Yanit yoksa tum sabitlemeleri kaldirir.

**Diger:**

`/admins`
Grup adminlerini listeler.

**Not:** Tum komutlar admin yetkisi gerektirir.
"""
    await callback_query.message.edit_text(text, reply_markup=get_back_button())


@router.callback_query(F.data == "help_connect")
async def help_connect_callback(callback_query: CallbackQuery, bot: Bot):
    """Bağlantı yardımı"""
    await callback_query.answer()

    text = """
**BAGLANTI SISTEMI**

Grubu ozelden yonetmenizi saglar.

**Nasil Calisir:**

1. Grupta `/connect` yazin
2. "Ozelden Devam Et" butonuna tiklayin
3. Bot'un ozel mesajinda grup komutlarini kullanin

**Komutlar:**

`/connect`
Grup icinde kullanin - ozel mesaja baglanti linki gonderir.

`/disconnect`
Ozelde kullanin - grup baglantisindan cikar.

`/status`
Ozelde kullanin - hangi gruba bagli oldugunuzu gosterir.

**Ozelden Kullanilabilir Komutlar:**
- `/filter` - Filter ekle
- `/filters` - Filterleri listele
- `/stop` - Filter sil
- `/stopall` - Tum filterleri sil
- `/adminonly` - Admin modunu ayarla

**Not:** Sadece grup adminleri baglanabilir.
"""
    await callback_query.message.edit_text(text, reply_markup=get_back_button())


@router.callback_query(F.data == "help_admin")
async def help_admin_callback(callback_query: CallbackQuery, bot: Bot):
    """Admin modu yardımı"""
    await callback_query.answer()

    text = """
**ADMIN MODU**

Bot komutlarini sadece adminlerin kullanmasini saglar.

**Komutlar:**

`/adminonly`
Mevcut durumu gosterir.

`/adminonly on`
Admin modunu aktif eder.
- Sadece adminler komut kullanabilir
- Diger kullanicilarin komutlari sessizce silinir

`/adminonly off`
Admin modunu kapatir.
- Herkes komut kullanabilir

**Varsayilan:** Admin modu ACIK

**Alternatif Komutlar:**
- `/adminonly acik` veya `/adminonly aktif`
- `/adminonly kapali` veya `/adminonly deaktif`

**Not:** Bu ayar grup bazlidir.
Her grup icin ayri ayarlanabilir.
"""
    await callback_query.message.edit_text(text, reply_markup=get_back_button())


@router.callback_query(F.data == "help_info")
async def help_info_callback(callback_query: CallbackQuery, bot: Bot):
    """Bilgi komutları yardımı"""
    await callback_query.answer()

    text = """
**BILGI KOMUTLARI**

`/start`
Botu baslatir ve karsilama mesaji gonderir.

`/help`
Bu yardim menusunu acar.

`/id`
- Kendi ID'nizi gosterir
- Bir mesaji yanitlayarak: o kisinin ID'sini gosterir
- Grupta: Grup ID'sini de gosterir

`/info`
- Detayli kullanici bilgisi gosterir
- Isim, soyisim, username, ID
- Bot mu, Premium mi vs.

**Bot Hakkinda:**
- **Ad:** {bot_name}
- **Surum:** {version}

**Ozellikler:**
- Otomatik uye kaydetme
- Sistem mesajlarini silme
- Filter sistemi
- Etiketleme sistemi
- Moderasyon araclari
""".format(bot_name=BOT_NAME, version=BOT_VERSION)

    await callback_query.message.edit_text(text, reply_markup=get_back_button())


# /connect command
@router.message(Command("connect"))
async def connect_command(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None

    if not user_id:
        return

    if message.chat.type == "private":
        await message.reply("Bu komut sadece gruplarda calisir!")
        return

    if not is_allowed_group(chat_id):
        return

    if not await is_admin(bot, chat_id, user_id):
        try:
            await message.delete()
        except Exception:
            pass
        return

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
    user_id = message.from_user.id if message.from_user else None

    if not user_id:
        return

    if message.chat.type != "private":
        if not is_allowed_group(chat_id):
            return

        if not await is_admin(bot, chat_id, user_id):
            try:
                await message.delete()
            except Exception:
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
    user_id = message.from_user.id if message.from_user else None

    if not user_id:
        return

    if message.chat.type != "private":
        if not is_allowed_group(chat_id):
            return

        if not await is_admin(bot, chat_id, user_id):
            try:
                await message.delete()
            except Exception:
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


# /disconnect command
@router.message(Command("disconnect"))
async def disconnect_command(message: Message, bot: Bot):
    """Disconnect from connected group"""
    if message.chat.type != "private":
        return

    if not message.from_user:
        return

    user_id = message.from_user.id
    connection = await get_user_connected_chat(user_id)

    if not connection:
        await message.reply("Hicbir gruba bagli degilsiniz!")
        return

    await disconnect_user(user_id)
    await message.reply(
        f"**{connection['chat_title']}** grubundan baglanti kesildi!\n\n"
        "Baska bir gruba baglanmak icin o grupta `/connect` yazin."
    )


# /status command
@router.message(Command("status"))
async def status_command(message: Message, bot: Bot):
    """Show current connection status"""
    if message.chat.type != "private":
        return

    if not message.from_user:
        return

    user_id = message.from_user.id
    connection = await get_user_connected_chat(user_id)

    if connection:
        await message.reply(
            f"**Baglanti Durumu**\n\n"
            f"Bagli grup: **{connection['chat_title']}**\n"
            f"Grup ID: `{connection['chat_id']}`\n\n"
            f"Bu gruptan ayrilmak icin /disconnect yazin."
        )
    else:
        await message.reply(
            "Hicbir gruba bagli degilsiniz!\n\n"
            "Bir gruba baglanmak icin o grupta `/connect` yazin."
        )
