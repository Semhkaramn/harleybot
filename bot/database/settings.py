from bot.database.connection import get_pool

async def get_chat_settings(chat_id: int) -> dict:
    """Get chat settings"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
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
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO chat_settings (chat_id, chat_locked)
            VALUES ($1, $2)
            ON CONFLICT (chat_id)
            DO UPDATE SET chat_locked = $2, updated_at = CURRENT_TIMESTAMP
        """, chat_id, locked)

async def is_chat_locked(chat_id: int) -> bool:
    """Check if chat is locked"""
    settings = await get_chat_settings(chat_id)
    return settings.get('chat_locked', False)

async def set_welcome_message(chat_id: int, message: str):
    """Set welcome message"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO chat_settings (chat_id, welcome_message, welcome_enabled)
            VALUES ($1, $2, TRUE)
            ON CONFLICT (chat_id)
            DO UPDATE SET welcome_message = $2, welcome_enabled = TRUE, updated_at = CURRENT_TIMESTAMP
        """, chat_id, message)

async def toggle_welcome(chat_id: int, enabled: bool):
    """Toggle welcome messages"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO chat_settings (chat_id, welcome_enabled)
            VALUES ($1, $2)
            ON CONFLICT (chat_id)
            DO UPDATE SET welcome_enabled = $2, updated_at = CURRENT_TIMESTAMP
        """, chat_id, enabled)

# Admin-only mode management
async def set_admin_only_mode(chat_id: int, enabled: bool):
    """Set admin-only command mode"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO chat_settings (chat_id, admin_only_commands, delete_non_admin_commands)
            VALUES ($1, $2, $2)
            ON CONFLICT (chat_id)
            DO UPDATE SET
                admin_only_commands = $2,
                delete_non_admin_commands = $2,
                updated_at = CURRENT_TIMESTAMP
        """, chat_id, enabled)

async def is_admin_only_mode(chat_id: int) -> bool:
    """Check if admin-only mode is enabled"""
    settings = await get_chat_settings(chat_id)
    return settings.get('admin_only_commands', True)

# Active tags management
async def start_tag_session(chat_id: int, message: str, started_by: int):
    """Start a new tag session"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO active_tags (chat_id, message, current_index, is_active, started_by)
            VALUES ($1, $2, 0, TRUE, $3)
            ON CONFLICT (chat_id)
            DO UPDATE SET message = $2, current_index = 0, is_active = TRUE, started_by = $3
        """, chat_id, message, started_by)

async def get_tag_session(chat_id: int) -> dict | None:
    """Get active tag session"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM active_tags
            WHERE chat_id = $1 AND is_active = TRUE
        """, chat_id)
    return dict(row) if row else None

async def update_tag_index(chat_id: int, new_index: int):
    """Update tag session index"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE active_tags SET current_index = $2
            WHERE chat_id = $1
        """, chat_id, new_index)

async def stop_tag_session(chat_id: int):
    """Stop tag session"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE active_tags SET is_active = FALSE
            WHERE chat_id = $1
        """, chat_id)
