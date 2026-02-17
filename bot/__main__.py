import asyncio
from pyrogram import Client, idle
from bot.config import API_ID, API_HASH, BOT_TOKEN, BOT_NAME
from bot.database.connection import init_db, close_db

# Import all handlers
from bot.handlers import basic, filters, tagger, admin

print(f"""
╔══════════════════════════════════════╗
║        {BOT_NAME} Bot                 ║
║     Rose Clone - Group Manager       ║
╚══════════════════════════════════════╝
""")

# Create bot client
app = Client(
    name="rose_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="bot.handlers")
)

async def main():
    """Main function to start the bot"""
    print("🚀 Starting bot...")

    # Initialize database
    await init_db()

    # Start the bot
    await app.start()

    me = await app.get_me()
    print(f"✅ Bot started as @{me.username}")
    print(f"📊 Bot ID: {me.id}")

    # Keep the bot running
    await idle()

    # Cleanup on shutdown
    print("🛑 Shutting down...")
    await close_db()
    await app.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
