from bot.database.connection import get_pool

async def save_member(chat_id: int, user_id: int, username: str = None, first_name: str = None):
    """Save or update a member"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO members (chat_id, user_id, username, first_name)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (chat_id, user_id)
            DO UPDATE SET username = $3, first_name = $4
        """, chat_id, user_id, username, first_name)

async def save_members_bulk(chat_id: int, members: list):
    """Save multiple members at once"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Delete old members first
        await conn.execute("DELETE FROM members WHERE chat_id = $1", chat_id)

        # Insert new members
        for member in members:
            await conn.execute("""
                INSERT INTO members (chat_id, user_id, username, first_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (chat_id, user_id) DO NOTHING
            """, chat_id, member['user_id'], member.get('username'), member.get('first_name'))

async def get_all_members(chat_id: int) -> list:
    """Get all members for a chat"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT user_id, username, first_name FROM members
            WHERE chat_id = $1
            ORDER BY id
        """, chat_id)
    return [dict(row) for row in rows]

async def get_members_count(chat_id: int) -> int:
    """Get member count for a chat"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT COUNT(*) as count FROM members
            WHERE chat_id = $1
        """, chat_id)
    return row['count'] if row else 0

async def get_members_batch(chat_id: int, offset: int, limit: int = 5) -> list:
    """Get batch of members for tagging"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT user_id, username, first_name FROM members
            WHERE chat_id = $1
            ORDER BY id
            OFFSET $2 LIMIT $3
        """, chat_id, offset, limit)
    return [dict(row) for row in rows]

async def delete_all_members(chat_id: int) -> int:
    """Delete all members for a chat"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM members WHERE chat_id = $1
        """, chat_id)
    count = int(result.split()[1]) if result else 0
    return count
