import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from bot.config import BOT_TOKEN, BOT_NAME
from bot.database.connection import init_db, close_db

# Import all routers
from bot.handlers.basic import router as basic_router
from bot.handlers.admin import router as admin_router
from bot.handlers.filters import router as filters_router
from bot.handlers.tagger import router as tagger_router
from bot.handlers.command_guard import router as guard_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print(f"""
╔══════════════════════════════════════╗
║        {BOT_NAME}                     ║
║     Grup Yonetim Botu                ║
║     Sadece BOT_TOKEN ile calisir!    ║
╚══════════════════════════════════════╝
""")

async def main():
    """Main function to start the bot"""

    if not BOT_TOKEN:
        print("❌ HATA: BOT_TOKEN bulunamadi!")
        print("📝 .env dosyasina BOT_TOKEN=your_token_here ekleyin")
        return

    print("🚀 Bot baslatiliyor...")

    # Initialize database
    await init_db()

    # Create bot and dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Register routers (order matters - guard first)
    dp.include_router(guard_router)
    dp.include_router(basic_router)
    dp.include_router(admin_router)
    dp.include_router(filters_router)
    dp.include_router(tagger_router)

    # Get bot info
    me = await bot.get_me()
    print(f"✅ Bot basladi: @{me.username}")
    print(f"📊 Bot ID: {me.id}")
    print(f"ℹ️  Sadece BOT_TOKEN ile calisiyor - API_ID/API_HASH gerekmiyor!")

    try:
        # Start polling
        await dp.start_polling(bot)
    finally:
        # Cleanup on shutdown
        print("🛑 Bot kapatiliyor...")
        await close_db()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
