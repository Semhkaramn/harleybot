from bot.database.connection import get_db, fetch_all, fetch_one, execute

async def get_chat_settings(chat_id: int) -> dict:
    """Get chat settings"""
    row = await fetch_one("""
        SELECT * FROM chat_settings WHERE chat_id = ?
    """, (chat_id,))

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
    db = await get_db()
    await db.execute("""
        INSERT INTO chat_settings (chat_id, chat_locked)
        VALUES (?, ?)
        ON CONFLICT (chat_id)
        DO UPDATE SET chat_locked = excluded.chat_locked, updated_at = CURRENT_TIMESTAMP
    """, (chat_id, 1 if locked else 0))
    await db.commit()

async def is_chat_locked(chat_id: int) -> bool:
    """Check if chat is locked"""
    settings = await get_chat_settings(chat_id)
    return settings.get('chat_locked', False)

async def set_welcome_message(chat_id: int, message: str):
    """Set welcome message"""
    db = await get_db()
    await db.execute("""
        INSERT INTO chat_settings (chat_id, welcome_message, welcome_enabled)
        VALUES (?, ?, 1)
        ON CONFLICT (chat_id)
        DO UPDATE SET welcome_message = excluded.welcome_message, welcome_enabled = 1, updated_at = CURRENT_TIMESTAMP
    """, (chat_id, message))
    await db.commit()

async def toggle_welcome(chat_id: int, enabled: bool):
    """Toggle welcome messages"""
    db = await get_db()
    await db.execute("""
        INSERT INTO chat_settings (chat_id, welcome_enabled)
        VALUES (?, ?)
        ON CONFLICT (chat_id)
        DO UPDATE SET welcome_enabled = excluded.welcome_enabled, updated_at = CURRENT_TIMESTAMP
    """, (chat_id, 1 if enabled else 0))
    await db.commit()

# Admin-only mode management
async def set_admin_only_mode(chat_id: int, enabled: bool):
    """Set admin-only command mode"""
    db = await get_db()
    await db.execute("""
        INSERT INTO chat_settings (chat_id, admin_only_commands, delete_non_admin_commands)
        VALUES (?, ?, ?)
        ON CONFLICT (chat_id)
        DO UPDATE SET
            admin_only_commands = excluded.admin_only_commands,
            delete_non_admin_commands = excluded.delete_non_admin_commands,
            updated_at = CURRENT_TIMESTAMP
    """, (chat_id, 1 if enabled else 0, 1 if enabled else 0))
    await db.commit()

async def is_admin_only_mode(chat_id: int) -> bool:
    """Check if admin-only mode is enabled"""
    settings = await get_chat_settings(chat_id)
    return settings.get('admin_only_commands', True)

# Active tags management
async def start_tag_session(chat_id: int, message: str, started_by: int):
    """Start a new tag session"""
    db = await get_db()
    await db.execute("""
        INSERT INTO active_tags (chat_id, message, current_index, is_active, started_by)
        VALUES (?, ?, 0, 1, ?)
        ON CONFLICT (chat_id)
        DO UPDATE SET message = excluded.message, current_index = 0, is_active = 1, started_by = excluded.started_by
    """, (chat_id, message, started_by))
    await db.commit()

async def get_tag_session(chat_id: int) -> dict | None:
    """Get active tag session"""
    row = await fetch_one("""
        SELECT * FROM active_tags
        WHERE chat_id = ? AND is_active = 1
    """, (chat_id,))
    return dict(row) if row else None

async def update_tag_index(chat_id: int, new_index: int):
    """Update tag session index"""
    db = await get_db()
    await db.execute("""
        UPDATE active_tags SET current_index = ?
        WHERE chat_id = ?
    """, (new_index, chat_id))
    await db.commit()

async def stop_tag_session(chat_id: int):
    """Stop tag session"""
    db = await get_db()
    await db.execute("""
        UPDATE active_tags SET is_active = 0
        WHERE chat_id = ?
    """, (chat_id,))
    await db.commit()
