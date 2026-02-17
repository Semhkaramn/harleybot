from bot.database.connection import get_db, fetch_one, fetch_all, execute


async def save_member(chat_id: int, user_id: int, username: str = None, first_name: str = None):
    """Save or update a member"""
    await execute("""
        INSERT INTO members (chat_id, user_id, username, first_name)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (chat_id, user_id)
        DO UPDATE SET username = EXCLUDED.username, first_name = EXCLUDED.first_name
    """, chat_id, user_id, username, first_name)


async def save_members_bulk(chat_id: int, members: list, replace_all: bool = False):
    """Save multiple members at once

    Args:
        chat_id: Chat ID
        members: List of member dictionaries
        replace_all: If True, delete existing members first (use with caution)
    """
    pool = await get_db()

    async with pool.acquire() as conn:
        # Only delete if explicitly requested AND we have new members to add
        if replace_all and members:
            await conn.execute("DELETE FROM members WHERE chat_id = $1", chat_id)

        # Insert or update members
        for member in members:
            await conn.execute("""
                INSERT INTO members (chat_id, user_id, username, first_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (chat_id, user_id)
                DO UPDATE SET username = EXCLUDED.username, first_name = EXCLUDED.first_name
            """, chat_id, member['user_id'], member.get('username'), member.get('first_name'))


async def get_all_members(chat_id: int) -> list:
    """Get all members for a chat"""
    rows = await fetch_all("""
        SELECT user_id, username, first_name FROM members
        WHERE chat_id = $1
        ORDER BY id
    """, chat_id)
    return rows


async def get_members_count(chat_id: int) -> int:
    """Get member count for a chat"""
    row = await fetch_one("""
        SELECT COUNT(*) as count FROM members
        WHERE chat_id = $1
    """, chat_id)
    return row['count'] if row else 0


async def get_members_batch(chat_id: int, offset: int, limit: int = 5) -> list:
    """Get batch of members for tagging"""
    rows = await fetch_all("""
        SELECT user_id, username, first_name FROM members
        WHERE chat_id = $1
        ORDER BY id
        LIMIT $2 OFFSET $3
    """, chat_id, limit, offset)
    return rows


async def delete_all_members(chat_id: int) -> int:
    """Delete all members for a chat"""
    pool = await get_db()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM members WHERE chat_id = $1
        """, chat_id)
        # Extract count from "DELETE X"
        count = int(result.split()[-1]) if result else 0
        return count
