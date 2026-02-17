import re
import random
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberAdministrator, ChatMemberOwner

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Check if user is admin in the chat"""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))
    except Exception:
        return False

async def is_owner(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Check if user is owner of the chat"""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return isinstance(member, ChatMemberOwner)
    except Exception:
        return False

async def can_restrict(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Check if user can restrict members"""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if isinstance(member, ChatMemberOwner):
            return True
        if isinstance(member, ChatMemberAdministrator):
            return member.can_restrict_members
        return False
    except Exception:
        return False

async def can_delete(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Check if user can delete messages"""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if isinstance(member, ChatMemberOwner):
            return True
        if isinstance(member, ChatMemberAdministrator):
            return member.can_delete_messages
        return False
    except Exception:
        return False

def get_user_mention(user_id: int, username: str = None, first_name: str = None) -> str:
    """Create a user mention"""
    if username:
        return f"@{username}"
    # Use first_name if available and not empty, otherwise create a user link with ID
    if first_name and first_name.strip():
        name = first_name.strip()
    else:
        name = f"Uye_{user_id}"
    return f"[{name}](tg://user?id={user_id})"

def get_user_link(user_id: int, first_name: str = None) -> str:
    """Create a clickable user link"""
    name = first_name or "Kullanici"
    return f"[{name}](tg://user?id={user_id})"

async def get_target_user(bot: Bot, message: Message) -> tuple:
    """Get target user from reply or mention

    Returns:
        tuple: (user_id, first_name/username)
        - If replying to message: returns (user_id, first_name)
        - If user_id provided: returns (user_id, first_name)
        - If @username provided: tries to resolve, returns (user_id, first_name) or (None, @username)
    """
    # Check if replying to a message (most reliable)
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
        return user.id, user.first_name

    # Check if user ID or username provided in command
    text = message.text or message.caption or ""
    args = text.split()[1:] if text else []

    if args:
        target = args[0].strip()

        # Handle @username
        if target.startswith("@"):
            username = target[1:]  # Remove @ prefix
            try:
                # Try to get user info via username
                # Note: This only works if user has interacted with the bot
                chat = await bot.get_chat(f"@{username}")
                if chat:
                    return chat.id, chat.first_name or username
            except Exception:
                pass
            # Return username for display purposes, ID is None
            return None, target

        # Handle user ID (can be negative for channels/groups)
        if target.lstrip('-').isdigit():
            try:
                user_id = int(target)
                chat = await bot.get_chat(user_id)
                return chat.id, getattr(chat, 'first_name', None) or getattr(chat, 'title', 'Kullanici')
            except Exception:
                # Return the ID even if we can't get details
                return int(target), "Kullanici"

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


# ==================== ROSE-STYLE FORMATTING ====================

def apply_fillings(text: str, user, chat=None) -> str:
    """Apply Rose-style fillings to text"""
    if not text:
        return text

    first_name = user.first_name or "Kullanici"
    last_name = user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    username = f"@{user.username}" if user.username else first_name
    mention = f"[{first_name}](tg://user?id={user.id})"
    chat_name = chat.title if chat else "Grup"

    replacements = {
        '{first}': first_name,
        '{last}': last_name,
        '{fullname}': full_name,
        '{username}': username,
        '{mention}': mention,
        '{id}': str(user.id),
        '{chatname}': chat_name,
    }

    for key, value in replacements.items():
        text = text.replace(key, value)

    return text


def parse_random_content(text: str) -> str:
    """Parse Rose-style random content using %%% separator"""
    if not text or '%%%' not in text:
        return text

    options = text.split('%%%')
    options = [opt.strip() for opt in options if opt.strip()]

    if options:
        return random.choice(options)
    return text


def parse_buttons_raw(text: str) -> tuple[str, list]:
    """Parse buttons from text and return serializable data for database storage"""
    if not text:
        return text, []

    buttons = []
    current_row = []

    # Pattern to match buttons: [Button Text](url) or [Button Text](url:same)
    # Supports both old buttonurl:// format and new simple format
    # Match: [text](buttonurl://url) or [text](buttonurl:url) or [text](http://url) or [text](https://url) or [text](tg://url)
    button_pattern = r'\[([^\]]+)\]\(((?:buttonurl:/?/?)?(?:https?://|tg://)[^)]+)\)'

    matches = re.findall(button_pattern, text)

    for btn_text, url_data in matches:
        # Check if :same is at the end
        same_line = url_data.endswith(':same')
        # Use proper string slicing instead of rstrip to avoid removing URL characters
        if same_line:
            url = url_data[:-5].strip()  # Remove ':same' (5 characters)
        else:
            url = url_data.strip()

        # Remove buttonurl:// or buttonurl: prefix if present
        url = re.sub(r'^buttonurl:/?/?', '', url)

        # Ensure URL has proper protocol
        if not url.startswith(('http://', 'https://', 'tg://')):
            url = 'https://' + url

        # Store as serializable dict instead of InlineKeyboardButton
        button_data = {'text': btn_text.strip(), 'url': url}

        if same_line and current_row:
            current_row.append(button_data)
        else:
            if current_row:
                buttons.append(current_row)
            current_row = [button_data]

    if current_row:
        buttons.append(current_row)

    cleaned_text = re.sub(button_pattern, '', text).strip()

    # Clean up extra whitespace and newlines
    cleaned_text = re.sub(r'\n\s*\n', '\n', cleaned_text)

    return cleaned_text, buttons


def parse_buttons(text: str) -> tuple[str, list]:
    """Parse buttons from text and return InlineKeyboardButton objects"""
    cleaned_text, raw_buttons = parse_buttons_raw(text)

    if not raw_buttons:
        return cleaned_text, []

    # Convert raw button data to InlineKeyboardButton objects
    buttons = []
    for row in raw_buttons:
        button_row = []
        for btn_data in row:
            button_row.append(InlineKeyboardButton(text=btn_data['text'], url=btn_data['url']))
        buttons.append(button_row)

    return cleaned_text, buttons


def build_keyboard(buttons: list) -> InlineKeyboardMarkup | None:
    """Build InlineKeyboardMarkup from button list (supports both raw dicts and InlineKeyboardButton objects)"""
    if not buttons:
        return None

    # Convert raw dicts to InlineKeyboardButton if needed
    keyboard_rows = []
    for row in buttons:
        button_row = []
        for btn in row:
            if isinstance(btn, dict):
                # Raw dict from database - convert to InlineKeyboardButton
                button_row.append(InlineKeyboardButton(text=btn['text'], url=btn['url']))
            else:
                # Already an InlineKeyboardButton
                button_row.append(btn)
        keyboard_rows.append(button_row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def extract_buttons_from_text(text: str) -> tuple[str, InlineKeyboardMarkup | None]:
    """Extract buttons and return cleaned text with keyboard"""
    cleaned_text, url_buttons = parse_buttons(text)

    if url_buttons:
        return cleaned_text, build_keyboard(url_buttons)

    return text, None


def process_filter_response(text: str, user, chat=None) -> tuple[str, InlineKeyboardMarkup | None]:
    """Process a filter response with all Rose-style features"""
    if not text:
        return "", None

    # Step 1: Random content
    text = parse_random_content(text)

    # Step 2: Apply fillings
    text = apply_fillings(text, user, chat)

    # Step 3: Extract buttons
    text, keyboard = extract_buttons_from_text(text)

    return text.strip(), keyboard


# ==================== COMMAND DETECTION ====================

BOT_COMMANDS = [
    'start', 'help', 'id', 'info', 'connect',
    'filter', 'filters', 'stop', 'stopall',
    'kaydet', 'uyeler', 'üyeler', 'temizle', 'naber', 'etiket', 'durdur', 'herkes',
    'ban', 'tban', 'dban', 'sban', 'unban',
    'kick', 'dkick', 'skick',
    'mute', 'tmute', 'dmute', 'smute', 'unmute',
    'lock', 'unlock', 'del', 'purge', 'pin', 'unpin', 'admins',
    'setadminonly', 'adminonly'
]

def is_bot_command(text: str) -> bool:
    """Check if message is a bot command"""
    if not text or not text.startswith('/'):
        return False

    parts = text.split()
    if not parts:
        return False

    cmd = parts[0][1:].lower()

    if '@' in cmd:
        cmd = cmd.split('@')[0]

    return cmd in BOT_COMMANDS


def extract_command_name(text: str) -> str | None:
    """Extract command name from message"""
    if not text or not text.startswith('/'):
        return None

    parts = text.split()
    if not parts:
        return None

    cmd = parts[0][1:].lower()

    if '@' in cmd:
        cmd = cmd.split('@')[0]

    return cmd
