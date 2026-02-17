from bot.database.connection import get_db, fetch_one, fetch_all, execute


async def save_member(chat_id: int, user_id: int, username: str = None, first_name: str = None):
    """Save or update a member"""
    await execute("""
        INSERT INTO members (chat_id, user_id, username, first_name)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (chat_id, user_id)
        DO UPDATE SET username = excluded.username, first_name = excluded.first_name
    """, (chat_id, user_id, username, first_name))


async def save_members_bulk(chat_id: int, members: list, replace_all: bool = False):
    """Save multiple members at once

    Args:
        chat_id: Chat ID
        members: List of member dictionaries
        replace_all: If True, delete existing members first (use with caution)
    """
    db = await get_db()

    # Only delete if explicitly requested AND we have new members to add
    if replace_all and members:
        await db.execute("DELETE FROM members WHERE chat_id = ?", (chat_id,))

    # Insert or update members
    for member in members:
        await db.execute("""
            INSERT INTO members (chat_id, user_id, username, first_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (chat_id, user_id)
            DO UPDATE SET username = excluded.username, first_name = excluded.first_name
        """, (chat_id, member['user_id'], member.get('username'), member.get('first_name')))

    await db.commit()


async def get_all_members(chat_id: int) -> list:
    """Get all members for a chat"""
    rows = await fetch_all("""
        SELECT user_id, username, first_name FROM members
        WHERE chat_id = ?
        ORDER BY id
    """, (chat_id,))
    return [dict(row) for row in rows]


async def get_members_count(chat_id: int) -> int:
    """Get member count for a chat"""
    row = await fetch_one("""
        SELECT COUNT(*) as count FROM members
        WHERE chat_id = ?
    """, (chat_id,))
    return row['count'] if row else 0


async def get_members_batch(chat_id: int, offset: int, limit: int = 5) -> list:
    """Get batch of members for tagging"""
    rows = await fetch_all("""
        SELECT user_id, username, first_name FROM members
        WHERE chat_id = ?
        ORDER BY id
        LIMIT ? OFFSET ?
    """, (chat_id, limit, offset))
    return [dict(row) for row in rows]


async def delete_all_members(chat_id: int) -> int:
    """Delete all members for a chat"""
    db = await get_db()
    async with db.execute("""
        DELETE FROM members WHERE chat_id = ?
    """, (chat_id,)) as cursor:
        await db.commit()
        return cursor.rowcount
