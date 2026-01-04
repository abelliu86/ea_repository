from sqlalchemy.orm import sessionmaker
from shared.db_models import get_engine, AccountSnapshot, OpenPosition
from dotenv import load_dotenv
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def check_data():
    engine = get_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    snapshots = session.query(AccountSnapshot).count()
    positions = session.query(OpenPosition).count()
    
    print(f"Account Snapshots: {snapshots}")
    print(f"Open Positions: {positions}")
    
    if snapshots > 0:
        latest = session.query(AccountSnapshot).order_by(AccountSnapshot.timestamp.desc()).first()
        print(f"Latest Snapshot: Account {latest.account_id} | Equity: {latest.equity} | Margin Lvl: {latest.margin_level}")
        
    session.close()

if __name__ == "__main__":
    check_data()
