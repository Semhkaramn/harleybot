import asyncpg
from bot.config import DATABASE_URL

pool = None

async def init_db():
    """Initialize database connection pool"""
    global pool
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=10,
        ssl="require"
    )
    await create_tables()
    print("✅ Database connected!")

async def get_pool():
    """Get database connection pool"""
    global pool
    if pool is None:
        await init_db()
    return pool

async def create_tables():
    """Create all necessary tables"""
    global pool
    async with pool.acquire() as conn:
        # Filters table - Enhanced for Rose-style filters
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS filters (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                keyword VARCHAR(255) NOT NULL,
                response TEXT,
                media_type VARCHAR(50),
                file_id TEXT,
                buttons TEXT,
                caption TEXT,
                filter_type VARCHAR(50) DEFAULT 'text',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, keyword)
            )
        """)

        # Add new columns if they don't exist (for migration)
        try:
            await conn.execute("ALTER TABLE filters ADD COLUMN IF NOT EXISTS media_type VARCHAR(50)")
            await conn.execute("ALTER TABLE filters ADD COLUMN IF NOT EXISTS file_id TEXT")
            await conn.execute("ALTER TABLE filters ADD COLUMN IF NOT EXISTS buttons TEXT")
            await conn.execute("ALTER TABLE filters ADD COLUMN IF NOT EXISTS caption TEXT")
            await conn.execute("ALTER TABLE filters ADD COLUMN IF NOT EXISTS filter_type VARCHAR(50) DEFAULT 'text'")
        except Exception:
            pass

        # Members table for tagger
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, user_id)
            )
        """)

        # Chat settings table - Enhanced
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id BIGINT PRIMARY KEY,
                chat_locked BOOLEAN DEFAULT FALSE,
                welcome_enabled BOOLEAN DEFAULT TRUE,
                welcome_message TEXT,
                admin_only_commands BOOLEAN DEFAULT TRUE,
                delete_non_admin_commands BOOLEAN DEFAULT TRUE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add new columns for admin-only feature
        try:
            await conn.execute("ALTER TABLE chat_settings ADD COLUMN IF NOT EXISTS admin_only_commands BOOLEAN DEFAULT TRUE")
            await conn.execute("ALTER TABLE chat_settings ADD COLUMN IF NOT EXISTS delete_non_admin_commands BOOLEAN DEFAULT TRUE")
        except Exception:
            pass

        # Active tags table (for ongoing tag sessions)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS active_tags (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT UNIQUE NOT NULL,
                message TEXT,
                current_index INT DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                started_by BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        print("✅ Tables created!")

async def close_db():
    """Close database connection"""
    global pool
    if pool:
        await pool.close()
