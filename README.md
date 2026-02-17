# Rose Clone Bot - Telegram Grup Yönetim Botu

Rose bot benzeri bir Telegram grup yönetim botu. Filter sistemi, etiketleme, ban/mute ve daha fazlası!

## Ozellikler

### Etiketleme Sistemi
- `/kaydet` - Tum uyeleri veritabanina kaydet
- `/uyeler` - Kayitli uye sayisi
- `/temizle` - Kayitli uyeleri sil
- `/naber` - Herkese rastgele soru sor (tek tek)
- `/etiket <mesaj>` - 5'erli etiketleme baslat
- `/durdur` - Etiketlemeyi durdur
- `/herkes <mesaj>` - Herkesi tek seferde etiketle

### Filter Sistemi
- `/filter <kelime> <yanit>` - Filter ekle
- `/filters` - Tum filterleri listele
- `/stop <kelime>` - Filter sil
- `/stopall` - Tum filterleri sil

### Admin Komutlari
- `/ban` - Kullanici banla
- `/unban` - Ban kaldir
- `/kick` - Kullanici at
- `/mute [sure]` - Sustur (orn: 1h, 30m, 1d)
- `/unmute` - Susturmayi kaldir
- `/lock` - Grubu kilitle (sadece adminler yazabilir)
- `/unlock` - Kilidi ac
- `/del` - Mesaj sil
- `/purge` - Toplu mesaj sil
- `/pin` - Mesaj sabitle
- `/unpin` - Sabitlemeyi kaldir
- `/admins` - Admin listesi

### Diger
- `/id` - ID bilgisi
- `/info` - Kullanici bilgisi
- `/help` - Yardim

## Kurulum

### 1. Gereksinimler

1. **Telegram API Bilgileri:**
   - https://my.telegram.org/apps adresinden API_ID ve API_HASH alin

2. **Bot Token:**
   - @BotFather'dan yeni bot olusturun ve token alin

3. **Neon PostgreSQL:**
   - https://neon.tech adresinden ucretsiz hesap olusturun
   - Yeni proje olusturun ve connection string'i kopyalayin

### 2. Environment Variables

`.env.example` dosyasini `.env` olarak kopyalayin ve doldurun:

```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
OWNER_ID=your_telegram_user_id
```

### 3. Lokal Calistirma

```bash
# Virtual environment olustur
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bagimliliklari yukle
pip install -r requirements.txt

# Botu calistir
python -m bot
```

## Heroku'da Deploy

### 1. Heroku CLI ile

```bash
# Heroku'ya giris yap
heroku login

# Yeni app olustur
heroku create your-bot-name

# Environment variables ekle
heroku config:set API_ID=your_api_id
heroku config:set API_HASH=your_api_hash
heroku config:set BOT_TOKEN=your_bot_token
heroku config:set DATABASE_URL=your_neon_database_url
heroku config:set OWNER_ID=your_telegram_user_id

# Deploy et
git push heroku main

# Worker'i etkinlestir
heroku ps:scale worker=1
```

### 2. Heroku Dashboard ile

1. https://dashboard.heroku.com adresine gidin
2. "New" -> "Create new app" tiklayin
3. App ismi verin ve olusturun
4. "Settings" -> "Config Vars" -> "Reveal Config Vars"
5. Tum environment variables'lari ekleyin:
   - `API_ID`
   - `API_HASH`
   - `BOT_TOKEN`
   - `DATABASE_URL`
   - `OWNER_ID`
6. "Deploy" sekmesine gidin
7. GitHub'a baglayin veya Heroku Git kullanin
8. Deploy edin
9. "Resources" sekmesinde `worker` dyno'yu etkinlestirin

## Onemli Notlar

- Bot'u gruba ekledikten sonra **admin yapin**
- Ban, mute gibi islemler icin **restrict members** yetkisi gerekli
- Etiketleme icin once `/kaydet` komutunu calistirin
- `/lock` komutu sadece adminlerin yazmasina izin verir

## Lisans

MIT License
