from pyrogram import Client
from pyrogram.types import Message, ChatMember
from pyrogram.enums import ChatMemberStatus
from bot.config import OWNER_ID

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user is admin in the chat (from Telegram)"""
    if user_id == OWNER_ID:
        return True

    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

async def is_owner(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user is owner of the chat"""
    if user_id == OWNER_ID:
        return True

    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status == ChatMemberStatus.OWNER
    except Exception:
        return False

async def can_restrict(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user can restrict members"""
    if user_id == OWNER_ID:
        return True

    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status == ChatMemberStatus.OWNER:
            return True
        if member.status == ChatMemberStatus.ADMINISTRATOR:
            return member.privileges.can_restrict_members
        return False
    except Exception:
        return False

async def can_delete(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user can delete messages"""
    if user_id == OWNER_ID:
        return True

    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status == ChatMemberStatus.OWNER:
            return True
        if member.status == ChatMemberStatus.ADMINISTRATOR:
            return member.privileges.can_delete_messages
        return False
    except Exception:
        return False

def get_user_mention(user_id: int, username: str = None, first_name: str = None) -> str:
    """Create a user mention"""
    if username:
        return f"@{username}"
    name = first_name or "Kullanıcı"
    return f"[{name}](tg://user?id={user_id})"

def get_user_link(user_id: int, first_name: str = None) -> str:
    """Create a clickable user link"""
    name = first_name or "Kullanıcı"
    return f"[{name}](tg://user?id={user_id})"

async def get_target_user(client: Client, message: Message) -> tuple:
    """Get target user from reply or mention"""
    user_id = None
    first_name = None

    # Check if replying to a message
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        if user:
            return user.id, user.first_name

    # Check if user ID or username provided in command
    args = message.text.split()[1:] if message.text else []
    if args:
        target = args[0]
        try:
            if target.startswith("@"):
                user = await client.get_users(target)
                return user.id, user.first_name
            elif target.isdigit():
                user = await client.get_users(int(target))
                return user.id, user.first_name
        except Exception:
            pass

    return None, None

def extract_time(time_str: str) -> int | None:
    """Extract seconds from time string like 1h, 30m, 1d"""
    if not time_str:
        return None

    time_str = time_str.lower().strip()

    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800
    }

    for suffix, mult in multipliers.items():
        if time_str.endswith(suffix):
            try:
                num = int(time_str[:-1])
                return num * mult
            except ValueError:
                return None

    # Try parsing as minutes if no suffix
    try:
        return int(time_str) * 60
    except ValueError:
        return None
