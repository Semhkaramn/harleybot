import os
from dotenv import load_dotenv

load_dotenv()

# Bot Token - THE ONLY REQUIRED CONFIGURATION
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Database - Using PostgreSQL (Neon.tech)
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Log Channel (optional)
_log_channel = os.getenv("LOG_CHANNEL_ID", "").strip()
LOG_CHANNEL_ID = int(_log_channel) if _log_channel and _log_channel.lstrip('-').isdigit() else None

# Allowed Group ID - Bot will ONLY work in this group
# Set this to your group's chat ID (negative number for groups/supergroups)
# Example: ALLOWED_GROUP_ID=-1001234567890
_allowed_group = os.getenv("ALLOWED_GROUP_ID", "").strip()
ALLOWED_GROUP_ID = int(_allowed_group) if _allowed_group and _allowed_group.lstrip('-').isdigit() else None

# Bot settings
BOT_NAME = "MsHarleyBot"
BOT_VERSION = "2.0.0"
