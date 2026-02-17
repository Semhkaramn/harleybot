from bot.database.connection import get_db, fetch_all, fetch_one, execute

async def get_chat_settings(chat_id: int) -> dict:
    """Get chat settings"""
    row = await fetch_one("""
        SELECT * FROM chat_settings WHERE chat_id = $1
    """, chat_id)

    if row:
        return dict(row)
    return {
        'chat_id': chat_id,
        'chat_locked': False,
        'welcome_enabled': True,
        'welcome_message': None,
        'admin_only_commands': True,
        'delete_non_admin_commands': True
    }

async def set_chat_locked(chat_id: int, locked: bool):
    """Set chat lock status"""
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO chat_settings (chat_id, chat_locked)
            VALUES ($1, $2)
            ON CONFLICT (chat_id)
            DO UPDATE SET chat_locked = EXCLUDED.chat_locked, updated_at = CURRENT_TIMESTAMP
        """, chat_id, 1 if locked else 0)

async def is_chat_locked(chat_id: int) -> bool:
    """Check if chat is locked"""
    settings = await get_chat_settings(chat_id)
    return bool(settings.get('chat_locked', 0))

async def set_welcome_message(chat_id: int, message: str):
    """Set welcome message"""
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO chat_settings (chat_id, welcome_message, welcome_enabled)
            VALUES ($1, $2, 1)
            ON CONFLICT (chat_id)
            DO UPDATE SET welcome_message = EXCLUDED.welcome_message, welcome_enabled = 1, updated_at = CURRENT_TIMESTAMP
        """, chat_id, message)

async def toggle_welcome(chat_id: int, enabled: bool):
    """Toggle welcome messages"""
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO chat_settings (chat_id, welcome_enabled)
            VALUES ($1, $2)
            ON CONFLICT (chat_id)
            DO UPDATE SET welcome_enabled = EXCLUDED.welcome_enabled, updated_at = CURRENT_TIMESTAMP
        """, chat_id, 1 if enabled else 0)

# Admin-only mode management
async def set_admin_only_mode(chat_id: int, enabled: bool):
    """Set admin-only command mode"""
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO chat_settings (chat_id, admin_only_commands, delete_non_admin_commands)
            VALUES ($1, $2, $3)
            ON CONFLICT (chat_id)
            DO UPDATE SET
                admin_only_commands = EXCLUDED.admin_only_commands,
                delete_non_admin_commands = EXCLUDED.delete_non_admin_commands,
                updated_at = CURRENT_TIMESTAMP
        """, chat_id, 1 if enabled else 0, 1 if enabled else 0)

async def is_admin_only_mode(chat_id: int) -> bool:
    """Check if admin-only mode is enabled"""
    settings = await get_chat_settings(chat_id)
    return settings.get('admin_only_commands', True)

# Active tags management
async def start_tag_session(chat_id: int, message: str, started_by: int):
    """Start a new tag session"""
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO active_tags (chat_id, message, current_index, is_active, started_by)
            VALUES ($1, $2, 0, 1, $3)
            ON CONFLICT (chat_id)
            DO UPDATE SET message = EXCLUDED.message, current_index = 0, is_active = 1, started_by = EXCLUDED.started_by
        """, chat_id, message, started_by)

async def get_tag_session(chat_id: int) -> dict | None:
    """Get active tag session"""
    row = await fetch_one("""
        SELECT * FROM active_tags
        WHERE chat_id = $1 AND is_active = 1
    """, chat_id)
    return dict(row) if row else None

async def update_tag_index(chat_id: int, new_index: int):
    """Update tag session index"""
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE active_tags SET current_index = $1
            WHERE chat_id = $2
        """, new_index, chat_id)

async def stop_tag_session(chat_id: int):
    """Stop tag session"""
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE active_tags SET is_active = 0
            WHERE chat_id = $1
        """, chat_id)
