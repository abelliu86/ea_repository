import streamlit as st
import os
import sys

# Setup Path
current_dir = os.path.dirname(os.path.abspath(__file__)) # analysis/pages
parent_dir = os.path.dirname(current_dir) # analysis
root_dir = os.path.dirname(parent_dir) # root
sys.path.append(root_dir)

from shared.db_models import get_engine, AppConfig
from analysis.shared.ui_components import apply_theme, THEMES
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
from datetime import datetime

load_dotenv(os.path.join(root_dir, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
engine = get_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# --- THEME MANAGEMENT ---
def get_config(key, default=None):
    try:
        with engine.connect() as conn:
            stmt = text("SELECT value FROM app_config WHERE key = :key")
            result = conn.execute(stmt, {"key": key}).scalar()
            return result if result else default
    except: return default

def save_config(key, value):
    try:
        with engine.connect() as conn:
            # Upsert
            stmt = text("""
                INSERT INTO app_config (key, value, updated_at) 
                VALUES (:key, :value, :time)
                ON CONFLICT(key) DO UPDATE SET value = :value, updated_at = :time
            """)
            conn.execute(stmt, {"key": key, "value": value, "time": datetime.utcnow()})
            conn.commit()
    except Exception as e:
        st.error(f"Save failed: {e}")

# Load Theme First
current_theme = get_config("ui_theme", "Light Mode")
st.set_page_config(page_title="Collector Config", layout="wide")
apply_theme(current_theme)

st.title("🔧 Collector Configuration")

# --- UI SETTINGS ---
with st.expander("🎨 Appearance Settings", expanded=True):
    themes = list(THEMES.keys())
    # Default index
    idx = 0
    if current_theme in themes:
        idx = themes.index(current_theme)
        
    sel_theme = st.selectbox("Dashboard Theme", themes, index=idx)
    
    if sel_theme != current_theme:
        if save_config("ui_theme", sel_theme):
            st.toast(f"Theme set to {sel_theme}. Reloading...")
            st.rerun()



def get_current_paths():
    val = get_config("mt5_paths")
    if val: return [p.strip() for p in val.split(";") if p.strip()]
    return []

def save_paths(new_paths):
    new_value = ";".join(new_paths)
    if save_config("mt5_paths", new_value):
        st.success("Config saved! Collector will auto-reload.")

st.markdown("### Manage MT5 Terminal Paths")
st.info("Settings are sync'd via Cloud Database.")

current_paths = get_current_paths()

# Use Session State to manage the list editing before saving
if "temp_paths" not in st.session_state:
    st.session_state.temp_paths = current_paths.copy()

# Sync if external change (optional, but keep simple for now)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Configured Paths")
    if not st.session_state.temp_paths:
        st.warning("No paths configured.")
    else:
        for i, path in enumerate(st.session_state.temp_paths):
            c_path, c_btn = st.columns([4, 1])
            c_path.code(path)
            if c_btn.button("❌ Remove", key=f"del_{i}"):
                st.session_state.temp_paths.pop(i)
                st.rerun()

with col2:
    st.subheader("Add New Path")
    new_path = st.text_input("Full Path to terminal64.exe")
    if st.button("➕ Add Path"):
        if new_path and new_path not in st.session_state.temp_paths:
            st.session_state.temp_paths.append(new_path)
            st.rerun()
        elif new_path in st.session_state.temp_paths:
            st.warning("Path already exists.")



if st.button("💾 Save Paths", type="primary"):
    save_paths(st.session_state.temp_paths)
    
if st.button("🔄 Reload from DB"):
    st.session_state.temp_paths = get_current_paths()
    st.rerun()



# --- ALIAS MANAGER ---
from shared.db_models import AccountAlias
from sqlalchemy import text

st.markdown("### 🏷️ Account Aliases")
st.info("Manage custom names for your accounts. These override auto-generated names.")

def get_aliases():
    try:
        session = Session()
        aliases = session.query(AccountAlias).all()
        session.close()
        return {a.account_id: a.alias for a in aliases}
    except Exception as e:
        st.error(f"Error fetching aliases: {e}")
        return {}

def get_known_accounts():
    try:
        session = Session()
        # Query distinct account_ids from trades table using raw SQL for speed/simplicity
        result = session.execute(text("SELECT DISTINCT account_id FROM trades ORDER BY account_id"))
        accounts = [str(row[0]) for row in result]
        session.close()
        return accounts
    except Exception as e:
        return []

def add_alias(acc_id, name):
    try:
        session = Session()
        # Ensure acc_id is string
        acc_id = str(acc_id)
        # Upsert
        alias = session.query(AccountAlias).filter_by(account_id=acc_id).first()
        if not alias:
            alias = AccountAlias(account_id=acc_id, alias=name)
            session.add(alias)
        else:
            alias.alias = name
            alias.updated_at = datetime.utcnow()
        session.commit()
        session.close()
        st.success(f"Saved alias for {acc_id}: {name}")
    except Exception as e:
        st.error(f"Error saving alias: {e}")

def delete_alias(acc_id):
    try:
        session = Session()
        acc_id = str(acc_id)
        session.query(AccountAlias).filter_by(account_id=acc_id).delete()
        session.commit()
        session.close()
        st.success(f"Deleted alias for {acc_id}")
    except Exception as e:
        st.error(f"Error deleting alias: {e}")

# UI for Aliases
current_aliases = get_aliases()
known_accounts = get_known_accounts()

with st.container():
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Add / Update Alias")
        with st.form("alias_form"):
            # Combine known accounts with manual entry option if needed, 
            # but selectbox + "allow_custom_values" isn't standard Streamlit.
            # Instead, we list accounts and have a text input fallback if empty selection?
            # Or just a selectbox. If user wants a new account not in DB yet, they can wait for data?
            
            # Prepare options: Existing in DB + Aliased ones
            options = sorted(list(set(known_accounts + list(current_aliases.keys()))))
            
            selected_acc = st.selectbox("Select Account ID", options=options)
            
            # Pre-fill alias if exists
            default_alias = current_aliases.get(selected_acc, "")
            
            alias_input = st.text_input("Alias Name", value=default_alias)
            
            if st.form_submit_button("Save Alias"):
                if alias_input and selected_acc:
                    add_alias(selected_acc, alias_input)
                    st.rerun()
                else:
                    st.warning("Please enter a name.")

    with c2:
        st.subheader("Existing Aliases")
        if current_aliases:
            # Display as a clean table with delete buttons
            for acc_id, name in current_aliases.items():
                r1, r2 = st.columns([3, 1])
                r1.text(f"{acc_id} ➝ {name}")
                if r2.button("🗑️", key=f"del_alias_{acc_id}"):
                    delete_alias(acc_id)
                    st.rerun()
        else:
            st.info("No aliases configured.")
