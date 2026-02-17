import json
import re
from bot.database.connection import get_db, fetch_one, fetch_all, execute


async def add_filter(
    chat_id: int,
    keyword: str,
    response: str = None,
    media_type: str = None,
    file_id: str = None,
    buttons: list = None,
    caption: str = None,
    filter_type: str = 'text'
) -> bool:
    """Add or update a filter with all Rose-style features"""
    # Serialize buttons to JSON if present
    buttons_json = json.dumps(buttons) if buttons else None

    await execute("""
        INSERT INTO filters (chat_id, keyword, response, media_type, file_id, buttons, caption, filter_type)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (chat_id, keyword)
        DO UPDATE SET
            response = EXCLUDED.response,
            media_type = EXCLUDED.media_type,
            file_id = EXCLUDED.file_id,
            buttons = EXCLUDED.buttons,
            caption = EXCLUDED.caption,
            filter_type = EXCLUDED.filter_type
    """, chat_id, keyword.lower(), response, media_type, file_id, buttons_json, caption, filter_type)
    return True


async def get_filter(chat_id: int, keyword: str) -> dict | None:
    """Get filter by keyword"""
    row = await fetch_one("""
        SELECT keyword, response, media_type, file_id, buttons, caption, filter_type
        FROM filters
        WHERE chat_id = $1 AND keyword = $2
    """, chat_id, keyword.lower())

    if not row:
        return None

    result = dict(row)
    # Deserialize buttons from JSON
    if result.get('buttons'):
        try:
            result['buttons'] = json.loads(result['buttons'])
        except (json.JSONDecodeError, TypeError):
            result['buttons'] = None
    return result


async def get_all_filters(chat_id: int) -> list:
    """Get all filters for a chat"""
    rows = await fetch_all("""
        SELECT keyword, response, media_type, file_id, buttons, caption, filter_type
        FROM filters
        WHERE chat_id = $1
        ORDER BY keyword
    """, chat_id)

    result = []
    for row in rows:
        filter_data = dict(row)
        # Deserialize buttons from JSON
        if filter_data.get('buttons'):
            try:
                filter_data['buttons'] = json.loads(filter_data['buttons'])
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Button JSON parse error: {e}")
                filter_data['buttons'] = None
        result.append(filter_data)
    return result


async def delete_filter(chat_id: int, keyword: str) -> bool:
    """Delete a filter"""
    pool = await get_db()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM filters
            WHERE chat_id = $1 AND keyword = $2
        """, chat_id, keyword.lower())
        return result != "DELETE 0"


async def delete_all_filters(chat_id: int) -> int:
    """Delete all filters for a chat"""
    pool = await get_db()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM filters WHERE chat_id = $1
        """, chat_id)
        # Extract count from "DELETE X"
        count = int(result.split()[-1]) if result else 0
        return count


async def check_filters(chat_id: int, text: str) -> dict | None:
    """Check if message matches any filter and return full filter data"""
    rows = await fetch_all("""
        SELECT keyword, response, media_type, file_id, buttons, caption, filter_type
        FROM filters
        WHERE chat_id = $1
    """, chat_id)

    text_lower = text.lower()

    for row in rows:
        keyword = row['keyword']
        matched = False

        # Handle different filter types
        if keyword.startswith('prefix:'):
            # Prefix filter - check if text starts with the prefix
            prefix = keyword[7:]  # Remove 'prefix:'
            matched = text_lower.startswith(prefix.lower())
        elif keyword.startswith('exact:'):
            # Exact filter - exact match only
            exact = keyword[6:]  # Remove 'exact:'
            matched = text_lower == exact.lower()
        else:
            # Regular filter - check if keyword is in text (word boundary)
            # Use word boundaries for better matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matched = bool(re.search(pattern, text_lower, re.IGNORECASE))

        if matched:
            result = dict(row)
            # Deserialize buttons from JSON
            if result.get('buttons'):
                try:
                    result['buttons'] = json.loads(result['buttons'])
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"Button JSON parse error: {e}")
                    result['buttons'] = None
            return result

    return None
