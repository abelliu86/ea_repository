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

from shared.db_models import get_engine, AccountSnapshot, OpenPosition, AccountAlias, AppConfig
from analysis.shared.ui_components import apply_theme, card_container, card_end
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load env from parent dir
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
Session = sessionmaker(bind=engine)

def get_theme():
    try:
        session = Session()
        conf = session.query(AppConfig).filter_by(key="ui_theme").first()
        session.close()
        return conf.value if conf else "Light Mode"
    except: return "Light Mode"

apply_theme(get_theme())

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
            # Fill NaN EA names with Magic Number immediately
            df['ea_name'] = df['ea_name'].fillna(df['magic_number'].astype(str))
        return df
    except Exception as e:
        st.error(f"Error connecting to DB: {e}")
        return pd.DataFrame()

def load_open_positions():
    if not engine: return pd.DataFrame()
    try:
        # Join with EAs table to get EA Name
        query = """
        SELECT 
            op.*, e.name as ea_name 
        FROM open_positions op
        LEFT JOIN eas e ON op.magic_number = e.magic_number AND op.account_id = e.account_id
        """
        df = pd.read_sql(query, engine)
        return df
    except: return pd.DataFrame()

def get_account_names(df):
    """
    Creates a mapping of account_id -> "Display Name".
    """
    mapping = {}
    
    # 1. Fetch Manual Aliases from DB
    try:
        session = Session()
        aliases = session.query(AccountAlias).all()
        db_aliases = {str(a.account_id): a.alias for a in aliases}
        session.close()
    except:
        db_aliases = {}
    
    # 2. Determine Dominant EA per Account
    if not df.empty and 'ea_name' in df.columns:
        ea_counts = df.groupby(['account_id', 'ea_name']).size().reset_index(name='count')
        ea_counts = ea_counts.sort_values(['account_id', 'count'], ascending=[True, False])
        dominant_eas = ea_counts.drop_duplicates('account_id')
        dominant_map = {str(row['account_id']): str(row['ea_name']) for _, row in dominant_eas.iterrows()}
    else:
        dominant_map = {}

    # 3. Build Mapping
    all_ids = df['account_id'].unique() if not df.empty else []
    for acc_id in all_ids:
        s_id = str(acc_id)
        if s_id in db_aliases:
            mapping[s_id] = db_aliases[s_id]
        elif s_id in dominant_map and dominant_map[s_id] not in ['nan', 'None']:
            mapping[s_id] = f"{s_id} ({dominant_map[s_id]})"
        else:
             mapping[s_id] = s_id
             
    return mapping

def load_snapshots():
    if not engine: return pd.DataFrame()
    try:
        # Get latest snapshot for each account
        query = """
        SELECT DISTINCT ON (account_id) *
        FROM account_snapshots
        ORDER BY account_id, timestamp DESC
        """
        df = pd.read_sql(query, engine)
        return df
    except: return pd.DataFrame()

st.title("🤖 EA Performance Repository")

if engine:
    with st.spinner("Loading Cloud Data..."):
        df = load_data()
        df_open = load_open_positions()
        df_snaps = load_snapshots()

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Filters")
    
    # Defaults
    start_date, end_date = datetime.utcnow().date(), datetime.utcnow().date()
    selected_accounts = []
    selected_eas = []
    selected_symbols = []

    if not df.empty:
        min_date = df['close_time'].min().date()
        max_date = df['close_time'].max().date()
        try:
             start_date, end_date = st.sidebar.date_input("Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)
        except:
             start_date, end_date = min_date, max_date

    # --- SHARED FILTERS ---
    if not df.empty:
        # Prepare Account Options with Aliases
        account_mapping = get_account_names(df)
        all_accounts = sorted(df['account_id'].unique())
        
        # Formatter function for the multiselect
        def format_account_name(acc_id):
            return account_mapping.get(str(acc_id), str(acc_id))

        selected_accounts = st.sidebar.multiselect(
            "Select Accounts", 
            options=sorted(df['account_id'].unique()), 
            default=df['account_id'].unique(),
            format_func=format_account_name
        )
        selected_eas = st.sidebar.multiselect("Select EAs", options=sorted(df['ea_name'].unique()), default=df['ea_name'].unique())
        selected_symbols = st.sidebar.multiselect("Select Symbols", options=sorted(df['symbol'].unique()), default=df['symbol'].unique())
    else:
        st.sidebar.info("No data to filter.")
        selected_accounts, selected_eas, selected_symbols = [], [], []

    # --- LIVE MONITOR ---
    st.subheader("🔴 Live Monitor")

    
    if df_snaps.empty:
        st.warning("No Live Data Available (Check Collector)")
    else:
        # Get Alias Mapping
        alias_map = get_account_names(df)
        
        # Filter Snapshots by Selected Accounts
        filtered_snaps = df_snaps.copy()
        if selected_accounts:
            filtered_snaps = filtered_snaps[filtered_snaps['account_id'].isin(selected_accounts)]

        # Display Live Metrics
        cols = st.columns(4)
        total_equity = filtered_snaps['equity'].sum()
        total_balance = filtered_snaps['balance'].sum()
        total_open_pnl = total_equity - total_balance
        
        cols[0].metric("Total Equity", f"${total_equity:,.2f}")
        cols[1].metric("Total Balance", f"${total_balance:,.2f}")
        cols[2].metric("Open PnL", f"${total_open_pnl:,.2f}", delta_color="normal")
        cols[3].metric("Active Accounts", len(filtered_snaps))
        
        # Open Positions Table
        if not df_open.empty:
            st.markdown("##### Open Positions")
            
            # Format and Enhance Open Positions
            show_cols = ['ticket', 'account_id', 'ea_name', 'symbol', 'type', 'volume', 'open_price', 'profit', 'sl', 'tp']
            
            # Apply Sidebar Filters to Open Positions
            open_mask = pd.Series(True, index=df_open.index)
            if selected_accounts:
                open_mask &= df_open['account_id'].isin(selected_accounts)
            if selected_eas:
                open_mask &= df_open['ea_name'].isin(selected_eas)
            if selected_symbols:
                open_mask &= df_open['symbol'].isin(selected_symbols)
                
            display_df = df_open[open_mask][show_cols].copy()
            
            # Apply Aliases
            display_df['account_id'] = display_df['account_id'].astype(str).map(lambda x: alias_map.get(x, x))
            
            st.dataframe(
                display_df,
                hide_index=True,
                column_config={
                    "profit": st.column_config.NumberColumn("PnL", format="$%.2f"),
                    "volume": st.column_config.NumberColumn("Lots", format="%.2f"),
                }
            )
        else:
            st.info("No Open Positions")

    


    # --- HISTORICAL ANALYSIS FILTERS ---
    # --- HISTORICAL ANALYSIS FILTERS ---
    # Filters are now applies globally above

    # --- APPLY FILTERS ---
    filtered_df = pd.DataFrame()
    if not df.empty:
        mask = (
            (df['close_time'].dt.date >= start_date) &
            (df['close_time'].dt.date <= end_date) &
            (df['ea_name'].isin(selected_eas)) &
            (df['symbol'].isin(selected_symbols)) &
            (df['account_id'].isin(selected_accounts))
        )
        filtered_df = df[mask].copy()

    # --- KPI CARDS (Consolidated) ---
    st.subheader("📈 Performance Overview")

    
    if filtered_df.empty:
        st.info("No historical trades found for selected range.")
    else:
        # Metric Calculations
        trade_mask = filtered_df['type'] != 'BALANCE'
        trades_only = filtered_df[trade_mask].copy()
        
        trades_only['net_profit'] = trades_only['profit'] + trades_only['commission'] + trades_only['swap']
        total_deposits = filtered_df[~trade_mask]['profit'].sum()
        
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
        max_drawdown = 0.0
        if not trades_only.empty:
            trades_only['cum_profit'] = trades_only['net_profit'].cumsum()
            running_equity = total_deposits + trades_only['cum_profit']
            running_max = running_equity.cummax()
            drawdown = (running_equity - running_max)
            max_drawdown = drawdown.min()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Net Profit", f"${net_profit:,.2f}", delta=f"{total_trades} trades")
        c2.metric("Profit Factor", f"{profit_factor:.2f}")
        c3.metric("Win Rate", f"{win_rate:.1f}%", f"{winning_trades}W / {losing_trades}L")
        c4.metric("Max Drawdown", f"${max_drawdown:,.2f}", delta_color="inverse")
    

    
    # --- CHARTS ---
    if not filtered_df.empty:
        c1, c2 = st.columns([2, 1])
        
        with c1:

            # Equity Curve
            st.markdown("#### Equity Growth")
            if not trades_only.empty:
                trades_only['cumulative_net'] = trades_only['net_profit'].cumsum()
                fig = px.line(trades_only, x='close_time', y='cumulative_net', markers=True)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#888'), margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)

            
        with c2:

            # Symbol Performance
            st.markdown("#### Top Symbols")
            sym_perf = filtered_df.groupby('symbol')['profit'].sum().reset_index().sort_values('profit', ascending=False).head(10)
            fig_sym = px.bar(sym_perf, x='profit', y='symbol', orientation='h', text_auto='.2s')
            fig_sym.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#888'), margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_sym, use_container_width=True)


        # Account Breakdown Table
        st.subheader("Account Breakdown")
        
        # Manual Aggregation to ensure clean DataFrame for Streamlit
        acc_data = []
        for account_id, group in trades_only.groupby('account_id'):
            pnl_series = group['profit'] + group['commission'] + group['swap']
            gross_profit = pnl_series[pnl_series > 0].sum()
            gross_loss = abs(pnl_series[pnl_series < 0].sum())
            
            pf = (gross_profit / gross_loss) if gross_loss != 0 else 0.0
            wr = (len(pnl_series[pnl_series > 0]) / len(group) * 100) if len(group) > 0 else 0.0
            
            acc_data.append({
                'account_id': str(account_id),
                'Trades': int(len(group)),
                'Net Profit': float(pnl_series.sum()),
                'Profit Factor': float(pf),
                'Win Rate': float(wr)
            })
            

        if not acc_data:
            account_perf = pd.DataFrame(columns=['account_id', 'Trades', 'Net Profit', 'Profit Factor', 'Win Rate'])
        else:
            account_perf = pd.DataFrame(acc_data)
        
        st.dataframe(
            account_perf,
            use_container_width=True,
            hide_index=True,
            column_config={
                "account_id": st.column_config.TextColumn("Account ID"),
                "Trades": st.column_config.NumberColumn("Trades", format="%d"),
                "Net Profit": st.column_config.NumberColumn("Net Profit", format="$%.2f"),
                "Profit Factor": st.column_config.NumberColumn("Profit Factor", format="%.2f"),
                "Win Rate": st.column_config.NumberColumn("Win Rate", format="%.1f%%")
            }
        )

        st.subheader("EA Breakdown")
        ea_perf = trades_only.groupby('ea_name')['net_profit'].sum().reset_index().sort_values('net_profit', ascending=False)
        st.bar_chart(ea_perf, x='ea_name', y='net_profit')

        st.subheader("Raw Data")
        st.dataframe(
            filtered_df, 
            hide_index=True, 
            use_container_width=False,
            column_config={
                "ticket": st.column_config.NumberColumn("Ticket", format="%d"),
                "magic_number": st.column_config.NumberColumn("Magic Number", format="%d"),
                "account_id": st.column_config.TextColumn("Account ID"),
            }
        )

else:
    st.error("Could not connect to database.")
