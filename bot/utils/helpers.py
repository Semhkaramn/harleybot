import re
import random
from pyrogram import Client
from pyrogram.types import Message, ChatMember, InlineKeyboardMarkup, InlineKeyboardButton
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
    name = first_name or "Kullanici"
    return f"[{name}](tg://user?id={user_id})"

def get_user_link(user_id: int, first_name: str = None) -> str:
    """Create a clickable user link"""
    name = first_name or "Kullanici"
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


# ==================== ROSE-STYLE FORMATTING ====================

def apply_fillings(text: str, user, chat=None) -> str:
    """Apply Rose-style fillings to text

    Supported fillings:
    {first} - User's first name
    {last} - User's last name
    {fullname} - User's full name
    {username} - User's username
    {mention} - Mentions the user
    {id} - User's ID
    {chatname} - Chat name
    """
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


def parse_buttons(text: str) -> tuple[str, list]:
    """Parse Rose-style buttons from text

    Syntax: [button text](buttonurl://url)
    Same line: [button](buttonurl://url:same)

    Returns: (cleaned_text, buttons_list)
    """
    if not text:
        return text, []

    buttons = []
    current_row = []

    # Pattern to match buttons: [text](buttonurl://url) or [text](buttonurl://url:same)
    button_pattern = r'\[([^\]]+)\]\(buttonurl://([^)]+)\)'

    # Find all buttons
    matches = re.findall(button_pattern, text)

    for btn_text, url_data in matches:
        # Check if it should be on the same line
        same_line = url_data.endswith(':same')
        url = url_data.rstrip(':same').strip()

        button = InlineKeyboardButton(text=btn_text.strip(), url=url)

        if same_line and current_row:
            # Add to current row
            current_row.append(button)
        else:
            # Start new row
            if current_row:
                buttons.append(current_row)
            current_row = [button]

    # Add last row
    if current_row:
        buttons.append(current_row)

    # Remove button markup from text
    cleaned_text = re.sub(button_pattern, '', text).strip()

    return cleaned_text, buttons


def parse_note_buttons(text: str) -> tuple[str, list]:
    """Parse buttons that link to notes

    Syntax: [button text](buttonurl://#notename)
    """
    if not text:
        return text, []

    # Pattern for note buttons
    note_pattern = r'\[([^\]]+)\]\(buttonurl://#([^):]+)(?::same)?\)'

    buttons = []
    current_row = []

    matches = re.findall(note_pattern, text)

    for btn_text, note_name in matches:
        # Note buttons will be handled as callback data
        button = InlineKeyboardButton(
            text=btn_text.strip(),
            callback_data=f"note_{note_name}"
        )
        current_row.append(button)
        buttons.append(current_row)
        current_row = []

    cleaned_text = re.sub(note_pattern, '', text).strip()

    return cleaned_text, buttons


def build_keyboard(buttons: list) -> InlineKeyboardMarkup | None:
    """Build InlineKeyboardMarkup from button list"""
    if not buttons:
        return None
    return InlineKeyboardMarkup(buttons)


def extract_buttons_from_text(text: str) -> tuple[str, InlineKeyboardMarkup | None]:
    """Extract buttons and return cleaned text with keyboard"""
    cleaned_text, url_buttons = parse_buttons(text)

    if url_buttons:
        return cleaned_text, build_keyboard(url_buttons)

    return text, None


def apply_markdown_formatting(text: str) -> str:
    """Apply Telegram-compatible markdown formatting

    Supports:
    *bold*
    _italic_
    __underline__
    ~strikethrough~
    `code`
    ||spoiler||
    """
    # Text is already in markdown format for Pyrogram
    return text


def process_filter_response(text: str, user, chat=None) -> tuple[str, InlineKeyboardMarkup | None]:
    """Process a filter response with all Rose-style features

    1. Random content selection (%%%)
    2. Fillings replacement
    3. Button extraction
    """
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

# List of all bot commands
BOT_COMMANDS = [
    # Basic commands
    'start', 'help', 'id', 'info',
    # Filter commands
    'filter', 'filters', 'stop', 'stopall',
    # Tagger commands
    'kaydet', 'uyeler', 'üyeler', 'temizle', 'naber', 'etiket', 'durdur', 'herkes',
    # Ban commands
    'ban', 'tban', 'dban', 'sban', 'unban',
    # Kick commands
    'kick', 'dkick', 'skick',
    # Mute commands
    'mute', 'tmute', 'dmute', 'smute', 'unmute',
    # Admin commands
    'lock', 'unlock', 'del', 'purge', 'pin', 'unpin', 'admins',
    # Settings commands
    'setadminonly', 'adminonly'
]

def is_bot_command(text: str) -> bool:
    """Check if message is a bot command"""
    if not text:
        return False

    text = text.strip()

    # Check if starts with /
    if not text.startswith('/'):
        return False

    # Extract command
    parts = text.split()
    if not parts:
        return False

    cmd = parts[0][1:].lower()  # Remove / prefix

    # Remove @botname suffix if present
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
