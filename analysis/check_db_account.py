from sqlalchemy import create_engine, text
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db_models import get_engine
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def check_accounts():
    engine = get_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT account_id FROM trades"))
        print("Unique Account IDs in DB:")
        for row in result:
            print(f"- {row[0]}")
            
        count = conn.execute(text("SELECT count(*) FROM trades")).scalar()
        print(f"Total Trades: {count}")

if __name__ == "__main__":
    check_accounts()
    
    # Check Schema
    engine = get_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("\nColumns in 'trades' table:")
        try:
            # Postgres specific query
            res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'trades'"))
            for r in res:
                print(f"- {r[0]} ({r[1]})")
        except Exception as e:
            print(f"Error checking trades schema: {e}")

    # Check Schema for EAS
    with engine.connect() as conn:
        print("\nColumns in 'eas' table:")
        try:
            res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'eas'"))
            for r in res:
                print(f"- {r[0]} ({r[1]})")
                
            print("\nContent of 'eas' table:")
            res = conn.execute(text("SELECT * FROM eas"))
            for r in res:
                print(r)
        except Exception as e:
             print(f"Could not query schema info: {e}")
