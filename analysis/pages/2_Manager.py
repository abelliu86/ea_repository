import streamlit as st
import pandas as pd
from sqlalchemy import text
import os
import sys

# Setup Path
current_dir = os.path.dirname(os.path.abspath(__file__)) # analysis/pages
parent_dir = os.path.dirname(current_dir) # analysis
root_dir = os.path.dirname(parent_dir) # root
sys.path.append(root_dir)

from shared.db_models import get_engine, EA
from dotenv import load_dotenv

load_dotenv(os.path.join(root_dir, ".env"))

st.set_page_config(page_title="EA Manager", layout="wide")
st.title("⚙️ EA Strategy Manager")

# DB Connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    st.error("DATABASE_URL not set")
    st.stop()

engine = get_engine(DATABASE_URL)

def load_eas():
    with engine.connect() as conn:
        return pd.read_sql("SELECT magic_number, account_id, name, description FROM eas ORDER BY account_id, name", conn)

def save_changes(edited_df):
    try:
        with engine.connect() as conn:
            with conn.begin():
                for index, row in edited_df.iterrows():
                    stmt = text("UPDATE eas SET name=:name, description=:desc WHERE magic_number=:magic AND account_id=:acc")
                    conn.execute(stmt, {"name": row['name'], "desc": row['description'], "magic": row['magic_number'], "acc": row['account_id']})
        st.success("Changes saved successfully!")
    except Exception as e:
        st.error(f"Error saving changes: {e}")

st.markdown("""
**How to Group EAs:**
Duplicate Magic Numbers can be grouped by giving them the **same Name**.
For example, rename `EA_101` and `EA_102` satisfyingly to `SuperBot`. result: Dashboard sums them up.
""")

df = load_eas()
if not df.empty:
    # Make magic_number disabled (key)
    edited_df = st.data_editor(
        df,
        column_config={
            "magic_number": st.column_config.NumberColumn(disabled=True),
            "account_id": st.column_config.NumberColumn(disabled=True, format="%d"),
            "name": st.column_config.TextColumn("Strategy Name (Editable)"),
            "description": st.column_config.TextColumn("Notes"),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed"
    )
    
    if st.button("💾 Save Changes"):
        save_changes(edited_df)
        st.rerun()
else:
    st.info("No EAs discovered yet. Run the Collector.")
