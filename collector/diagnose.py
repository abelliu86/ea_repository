import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db_models import get_engine, Base

def check_db_health():
    print("--- Starting DB Health Check ---")
    
    # 1. Load Env
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("[ERROR] DATABASE_URL not found in .env")
        return
        
    print(f"[OK] Found DATABASE_URL")
    
    try:
        engine = get_engine(db_url)
        with engine.connect() as conn:
            print("[OK] Database Connected")
            
            # 2. Check EAS Schema
            print("Checking 'eas' table schema...")
            try:
                # Check for account_id column
                # This works for Postgres
                res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'eas' AND column_name = 'account_id'"))
                if res.rowcount == 0 and res.fetchone() is None:
                     print("[CRITICAL ERROR] 'account_id' column MISSING in 'eas' table.")
                     print(">> CAUSE: You updated the code but did not reset the database.")
                     print(">> FIX: Run 'python collector/init_db.py' or manually drop the 'eas' table.")
                else:
                    print("[OK] 'account_id' column exists in 'eas'.")
                    
                    # Check PK (Optional/Harder to query safely cross-db, skipping for now)
                    
            except Exception as e:
                print(f"[WARN] Could not query information_schema: {e}")
                # Fallback: Try a select
                try:
                    conn.execute(text("SELECT account_id FROM eas LIMIT 1"))
                    print("[OK] Select 'account_id' succeeded.")
                except Exception as e2:
                    print(f"[CRITICAL] Cannot select 'account_id' from eas. Column likely missing. Error: {e2}")

            # 3. Check TRADES Schema
            print("Checking 'trades' table schema...")
            try:
                res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'trades' AND column_name = 'account_id'"))
                if res.rowcount == 0 and res.fetchone() is None:
                     print("[CRITICAL ERROR] 'account_id' column MISSING in 'trades' table.")
                else:
                    print("[OK] 'account_id' column exists in 'trades'.")
            except:
                pass

    except Exception as e:
        print(f"[CHECK FAILED] Connection Failed: {e}")

    print("--- Check Complete ---")

if __name__ == "__main__":
    check_db_health()
