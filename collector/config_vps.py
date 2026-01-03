import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# Database Connection String
# Load from .env (which should be in the root directory for local dev, or same dir for VPS)
# We traverse up 2 directories to find .env if running from collector/
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback/Warning
    print("WARNING: DATABASE_URL not found in env. Using local SQLite.")
    DATABASE_URL = "sqlite:///../../data/eas_local_poc.db"

# MT5 Connection Settings
# Path to your MT5 terminal.exe if not in default location (optional)
# MT5 Configuration
# Supports multiple paths separated by semicolon ';'
_mt5_raw = os.getenv("MT5_PATH", "")
MT5_PATHS = [p.strip() for p in _mt5_raw.split(";") if p.strip()]

# Logging
LOG_LEVEL = "INFO"
