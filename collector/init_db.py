import sys
import os
import logging

# Add parent directory to path so we can import shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db_models import Base, get_engine, create_tables
from collector.config_vps import DATABASE_URL

# Setup basic logging
logging.basicConfig(level=logging.INFO)

def main():
    print(f"Connecting to database...")
    # Mask password for safety in logs
    safe_url = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else "..."
    print(f"Target: ...@{safe_url}")
    
    try:
        engine = get_engine(DATABASE_URL)
        print("Engine created. Creating tables...")
        # Base.metadata.drop_all(engine) # SAFETY: Commented out to prevent accidental wipe
        Base.metadata.create_all(engine) # Will create app_config if missing
        print("SUCCESS! Tables 'eas' and 'trades' created (or already existed).")
    except Exception as e:
        print(f"FAILED to initialize database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
