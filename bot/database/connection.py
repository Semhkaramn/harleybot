import aiosqlite
from bot.config import DATABASE_PATH

db = None


async def init_db():
    """Initialize database connection"""
    global db
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await create_tables()
    print("✅ Database connected!")


async def get_db():
    """Get database connection"""
    global db
    if db is None:
        await init_db()
    return db


async def fetch_one(query: str, params: tuple = ()):
    """Fetch one row from database"""
    database = await get_db()
    async with database.execute(query, params) as cursor:
        row = await cursor.fetchone()
        return row


async def fetch_all(query: str, params: tuple = ()):
    """Fetch all rows from database"""
    database = await get_db()
    async with database.execute(query, params) as cursor:
        rows = await cursor.fetchall()
        return rows


async def execute(query: str, params: tuple = ()):
    """Execute a query"""
    database = await get_db()
    await database.execute(query, params)
    await database.commit()


async def executemany(query: str, params_list: list):
    """Execute many queries"""
    database = await get_db()
    await database.executemany(query, params_list)
    await database.commit()


async def create_tables():
    """Create all necessary tables"""
    database = await get_db()

    # Filters table - Enhanced for Rose-style filters
    await database.execute("""
        CREATE TABLE IF NOT EXISTS filters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            keyword TEXT NOT NULL,
            response TEXT,
            media_type TEXT,
            file_id TEXT,
            buttons TEXT,
            caption TEXT,
            filter_type TEXT DEFAULT 'text',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_id, keyword)
        )
    """)

    # Members table for tagger
    await database.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_id, user_id)
        )
    """)

    # Chat settings table - Enhanced
    await database.execute("""
        CREATE TABLE IF NOT EXISTS chat_settings (
            chat_id INTEGER PRIMARY KEY,
            chat_locked INTEGER DEFAULT 0,
            welcome_enabled INTEGER DEFAULT 1,
            welcome_message TEXT,
            admin_only_commands INTEGER DEFAULT 1,
            delete_non_admin_commands INTEGER DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Active tags table (for ongoing tag sessions)
    await database.execute("""
        CREATE TABLE IF NOT EXISTS active_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE NOT NULL,
            message TEXT,
            current_index INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            started_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await database.commit()
    print("✅ Tables created!")


async def close_db():
    """Close database connection"""
    global db
    if db:
        await db.close()
        db = None
