import asyncpg
from bot.config import DATABASE_URL

pool = None


async def init_db():
    """Initialize database connection pool"""
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    await create_tables()


async def get_db():
    """Get database connection from pool"""
    global pool
    if pool is None:
        await init_db()
    return pool


async def fetch_one(query: str, *args):
    """Fetch one row from database"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args):
    """Fetch all rows from database"""
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def execute(query: str, *args):
    """Execute a query"""
    async with pool.acquire() as conn:
        await conn.execute(query, *args)


async def executemany(query: str, params_list: list):
    """Execute many queries"""
    async with pool.acquire() as conn:
        await conn.executemany(query, params_list)


async def create_tables():
    """Create all necessary tables"""
    async with pool.acquire() as conn:
        # Filters table - Enhanced for Rose-style filters
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS filters (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
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
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                username TEXT,
                first_name TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, user_id)
            )
        """)

        # Chat settings table - Enhanced
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id BIGINT PRIMARY KEY,
                chat_locked INTEGER DEFAULT 0,
                welcome_enabled INTEGER DEFAULT 1,
                welcome_message TEXT,
                admin_only_commands INTEGER DEFAULT 1,
                delete_non_admin_commands INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Active tags table (for ongoing tag sessions)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS active_tags (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT UNIQUE NOT NULL,
                message TEXT,
                current_index INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                started_by BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # User connections table (for private chat management)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_connections (
                user_id BIGINT PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                chat_title TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


async def close_db():
    """Close database connection pool"""
    global pool
    if pool:
        await pool.close()
        pool = None
