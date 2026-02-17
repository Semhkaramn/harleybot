import os
from dotenv import load_dotenv

load_dotenv()

# Bot Token - THE ONLY REQUIRED CONFIGURATION
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Database - Using SQLite (no external database required)
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_data.db")

# Log Channel (optional)
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0")) if os.getenv("LOG_CHANNEL_ID") else None

# Allowed Group ID - Bot will ONLY work in this group
# Set this to your group's chat ID (negative number for groups/supergroups)
# Example: ALLOWED_GROUP_ID=-1001234567890
ALLOWED_GROUP_ID = int(os.getenv("ALLOWED_GROUP_ID", "0")) if os.getenv("ALLOWED_GROUP_ID") else None

# Bot settings
BOT_NAME = "HarleyBot"
BOT_VERSION = "2.0.0"
