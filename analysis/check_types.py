import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Path setup needed BEFORE importing shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db_models import get_engine
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

engine = get_engine(os.getenv("DATABASE_URL"))

try:
    with engine.connect() as conn:
        print("--- Trade Types ---")
        df = pd.read_sql("SELECT DISTINCT type FROM trades", conn)
        print(df)
        print("\n--- Sample Trade ---")
        df_sample = pd.read_sql("SELECT * FROM trades LIMIT 1", conn)
        print(df_sample.to_string())
except Exception as e:
    print(e)
