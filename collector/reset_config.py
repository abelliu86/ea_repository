import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import sessionmaker
from shared.db_models import get_engine, AppConfig
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def reset_config():
    engine = get_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Default Paths + User Requested Path
    # Note: Assuming 'terminal64.exe' is the target executable based on previous paths.
    default_paths = r"C:\Program Files\Darwinex MetaTrader 5\terminal64.exe;C:\Program Files\MetaTrader 5\terminal64.exe;C:\Program Files\MetaTrader 5-5\terminal64.exe"
    
    config = session.query(AppConfig).filter_by(key="mt5_paths").first()
    if config:
        config.value = default_paths
    else:
        config = AppConfig(key="mt5_paths", value=default_paths)
        session.add(config)
        
    session.commit()
    print("Reset 'mt5_paths' in DB to default.")
    session.close()

if __name__ == "__main__":
    reset_config()
