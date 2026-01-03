import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os
import sys

# Perform absolute import of shared/db_models
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from shared.db_models import get_engine
from dotenv import load_dotenv

# Load env from parent dir
load_dotenv(os.path.join(parent_dir, ".env"))

st.set_page_config(page_title="EA Repository", layout="wide")

# Database Connection
@st.cache_resource
def get_db_engine():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        st.error("DATABASE_URL not found. Please set it in .env")
        return None
    return get_engine(db_url)

engine = get_db_engine()

# Fetch Data
def load_data():
    if not engine:
        return pd.DataFrame()
    
    query = """
    SELECT 
        t.ticket, t.symbol, t.type, t.volume, t.profit, t.commission, t.swap, t.close_time, t.magic_number, t.account_id,
        e.name as ea_name
    FROM trades t
    LEFT JOIN eas e ON t.magic_number = e.magic_number AND t.account_id = e.account_id
    ORDER BY t.close_time ASC
    """
    try:
        df = pd.read_sql(query, engine)
        if not df.empty:
            df['close_time'] = pd.to_datetime(df['close_time'])
        return df
    except Exception as e:
        st.error(f"Error connecting to DB: {e}")
        return pd.DataFrame()

st.title("🤖 EA Performance Repository")

if engine:
    with st.spinner("Loading trades from Cloud DB..."):
        df = load_data()

    if df.empty:
        st.warning("No trades found in the database yet. Run the Collector on your VPS!")
    else:
        # Sidebar Filters
        st.sidebar.header("Filters")
        
        # Date Filter
        min_date = df['close_time'].min().date()
        max_date = df['close_time'].max().date()
        
        try:
             start_date, end_date = st.sidebar.date_input(
                "Date Range", 
                [min_date, max_date],
                min_value=min_date,
                max_value=max_date
            )
        except:
             start_date, end_date = min_date, max_date

        selected_accounts = st.sidebar.multiselect("Select Accounts", options=df['account_id'].unique(), default=df['account_id'].unique())
        selected_eas = st.sidebar.multiselect("Select EAs", options=df['ea_name'].unique(), default=df['ea_name'].unique())
        selected_symbols = st.sidebar.multiselect("Select Symbols", options=df['symbol'].unique(), default=df['symbol'].unique())

        # Filter Logic
        mask = (
            (df['close_time'].dt.date >= start_date) &
            (df['close_time'].dt.date <= end_date) &
            (df['ea_name'].isin(selected_eas)) &
            (df['symbol'].isin(selected_symbols)) &
            (df['account_id'].isin(selected_accounts))
        )
        filtered_df = df[mask].copy()

        # Metric Calculations
        # 1. Net Profit (Trading Profit) - Exclude Balance Ops
        trade_mask = filtered_df['type'] != 'BALANCE'
        trades_only = filtered_df[trade_mask].copy()
        
        # Determine actual PnL (Net Profit = Profit + Commission + Swap)
        # Note: If your DB 'profit' already includes them, verify. Usually MT5 'profit' is gross.
        trades_only['net_profit'] = trades_only['profit'] + trades_only['commission'] + trades_only['swap']
        
        # 2. Balance Operations
        balance_ops = filtered_df[~trade_mask]
        total_deposits = balance_ops['profit'].sum() # Assuming deposits are in 'profit' column for DEAL_TYPE_BALANCE
        
        # Metrics
        net_profit = trades_only['net_profit'].sum()
        gross_profit = trades_only[trades_only['net_profit'] > 0]['net_profit'].sum()
        gross_loss = trades_only[trades_only['net_profit'] < 0]['net_profit'].sum()
        
        total_trades = len(trades_only)
        winning_trades = len(trades_only[trades_only['net_profit'] > 0])
        losing_trades = len(trades_only[trades_only['net_profit'] < 0])
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else float('inf')
        
        # Max Drawdown
        if not trades_only.empty:
            trades_only['cum_profit'] = trades_only['net_profit'].cumsum()
            # If you want correct Equity Drawdown, you need (Initial Deposit + Cumulative Profit)
            # We will approximate with Cumulative PnL curve
            running_equity = total_deposits + trades_only['cum_profit']
            running_max = running_equity.cummax()
            drawdown = (running_equity - running_max)
            max_drawdown = drawdown.min()
            
            # Drawdown as %? 
            # max_drawdown_pct = (drawdown / running_max).min() * 100
        else:
            max_drawdown = 0.0

        st.markdown("### 📊 Key Performance Indicators")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Net Profit", f"${net_profit:,.2f}", delta=f"{len(trades_only)} trades")
        c2.metric("Profit Factor", f"{profit_factor:.2f}")
        c3.metric("Win Rate", f"{win_rate:.1f}%", f"{winning_trades}W / {losing_trades}L")
        c4.metric("Max Drawdown ($)", f"${max_drawdown:,.2f}")

        # Charts
        st.subheader("Equity Curve (Net)")
        if not trades_only.empty:
            # We want to show the equity evolution
            # We need to re-merge balance ops to get true equity, OR just show trading PnL curve
            # Let's show Trading Growth for now
            trades_only['cumulative_net'] = trades_only['net_profit'].cumsum()
            fig = px.line(trades_only, x='close_time', y='cumulative_net', title="Trading PnL Growth (Excl. Deposits)", markers=True)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("EA Breakdown")
        ea_perf = trades_only.groupby('ea_name')['net_profit'].sum().reset_index().sort_values('net_profit', ascending=False)
        st.bar_chart(ea_perf, x='ea_name', y='net_profit')

        st.subheader("Raw Data")
        st.dataframe(filtered_df)

else:
    st.error("Could not connect to database.")
