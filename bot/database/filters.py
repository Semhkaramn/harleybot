from bot.database.connection import get_pool

async def add_filter(chat_id: int, keyword: str, response: str) -> bool:
    """Add or update a filter"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO filters (chat_id, keyword, response)
            VALUES ($1, $2, $3)
            ON CONFLICT (chat_id, keyword)
            DO UPDATE SET response = $3
        """, chat_id, keyword.lower(), response)
    return True

async def get_filter(chat_id: int, keyword: str) -> str | None:
    """Get filter response by keyword"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT response FROM filters
            WHERE chat_id = $1 AND keyword = $2
        """, chat_id, keyword.lower())
    return row['response'] if row else None

async def get_all_filters(chat_id: int) -> list:
    """Get all filters for a chat"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT keyword, response FROM filters
            WHERE chat_id = $1
            ORDER BY keyword
        """, chat_id)
    return [dict(row) for row in rows]

async def delete_filter(chat_id: int, keyword: str) -> bool:
    """Delete a filter"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM filters
            WHERE chat_id = $1 AND keyword = $2
        """, chat_id, keyword.lower())
    return "DELETE 1" in result

async def delete_all_filters(chat_id: int) -> int:
    """Delete all filters for a chat"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM filters WHERE chat_id = $1
        """, chat_id)
    # Extract count from result like "DELETE 5"
    count = int(result.split()[1]) if result else 0
    return count

async def check_filters(chat_id: int, text: str) -> str | None:
    """Check if message matches any filter"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT keyword, response FROM filters
            WHERE chat_id = $1
        """, chat_id)

    text_lower = text.lower()
    for row in rows:
        keyword = row['keyword']
        # Check if keyword is in message (word boundary check)
        if keyword in text_lower:
            return row['response']
    return None
