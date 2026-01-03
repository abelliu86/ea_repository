import streamlit as st
import os
import sys

# Setup Path
current_dir = os.path.dirname(os.path.abspath(__file__)) # analysis/pages
parent_dir = os.path.dirname(current_dir) # analysis
root_dir = os.path.dirname(parent_dir) # root
sys.path.append(root_dir)

from shared.db_models import get_engine, AppConfig
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv(os.path.join(root_dir, ".env"))

st.set_page_config(page_title="Collector Config", layout="wide")
st.title("🔧 Collector Configuration (Cloud Synced)")

DATABASE_URL = os.getenv("DATABASE_URL")
engine = get_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def get_current_paths():
    try:
        session = Session()
        config = session.query(AppConfig).filter_by(key="mt5_paths").first()
        session.close()
        
        if config and config.value:
            return [p.strip() for p in config.value.split(";") if p.strip()]
        return []
    except Exception as e:
        st.error(f"DB Error: {e}")
        return []

def save_paths(new_paths):
    new_value = ";".join(new_paths)
    try:
        session = Session()
        config = session.query(AppConfig).filter_by(key="mt5_paths").first()
        if not config:
            config = AppConfig(key="mt5_paths", value=new_value)
            session.add(config)
        else:
            config.value = new_value
        
        session.commit()
        session.close()
            
        st.success("Configuration saved to Cloud Database! Collector will auto-reload.")
    except Exception as e:
        st.error(f"Error saving to DB: {e}")

st.markdown("### Manage MT5 Terminal Paths")
st.info("Settings are now stored in the database. Your VPS will pick them up automatically.")

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

st.divider()

if st.button("💾 Save Configuration to .env", type="primary"):
    save_paths(st.session_state.temp_paths)
    
if st.button("🔄 Reload from File (Discard Unsaved)"):
    st.session_state.temp_paths = get_current_paths()
    st.rerun()
