import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Setup Path
current_dir = os.path.dirname(os.path.abspath(__file__)) # analysis/pages
parent_dir = os.path.dirname(current_dir) # analysis
root_dir = os.path.dirname(parent_dir) # root
sys.path.append(root_dir)

from shared.db_models import get_engine, AccountAlias, AppConfig
from analysis.shared.ui_components import apply_theme, card_container, card_end
from dotenv import load_dotenv

load_dotenv(os.path.join(root_dir, ".env"))

# --- DB & THEME ---
DATABASE_URL = os.getenv("DATABASE_URL")
engine = get_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def get_theme():
    try:
        session = Session()
        conf = session.query(AppConfig).filter_by(key="ui_theme").first()
        session.close()
        return conf.value if conf else "Light Mode"
    except: return "Light Mode"

st.set_page_config(page_title="Risk Analysis", layout="wide")
apply_theme(get_theme())

def get_account_names(df):
    mapping = {}
    if not engine: return mapping
    try:
        session = Session()
        aliases = session.query(AccountAlias).all()
        db_aliases = {str(a.account_id): a.alias for a in aliases}
        session.close()
    except: db_aliases = {}
    
    dominant_map = {}
    if not df.empty and 'ea_name' in df.columns:
        ea_counts = df.groupby(['account_id', 'ea_name']).size().reset_index(name='count')
        ea_counts = ea_counts.sort_values(['account_id', 'count'], ascending=[True, False])
        dominant_eas = ea_counts.drop_duplicates('account_id')
        dominant_map = {str(row['account_id']): str(row['ea_name']) for _, row in dominant_eas.iterrows()}

    for acc in df['account_id'].unique():
        s = str(acc)
        if s in db_aliases: mapping[s] = db_aliases[s]
        elif s in dominant_map and dominant_map[s] not in ['nan', 'None']:
            mapping[s] = f"{s} ({dominant_map[s]})"
        else: mapping[s] = s
    return mapping

def load_trades():
    if not engine: return pd.DataFrame()
    query = """
    SELECT 
        t.ticket, t.symbol, t.type, t.volume, t.profit, t.commission, t.swap, 
        t.close_time, t.magic_number, t.account_id,
        e.name as ea_name
    FROM trades t
    LEFT JOIN eas e ON t.magic_number = e.magic_number AND t.account_id = e.account_id
    WHERE t.type IN ('BUY', 'SELL')
    ORDER BY t.close_time ASC
    """
    try:
        df = pd.read_sql(query, engine)
        if not df.empty:
            df['close_time'] = pd.to_datetime(df['close_time'])
            df['ea_name'] = df['ea_name'].fillna(df['magic_number'].astype(str))
            df['net_profit'] = df['profit'] + df['commission'] + df['swap']
        return df
    except Exception as e:
        st.error(f"Data Error: {e}")
        return pd.DataFrame()

# --- MAIN PAGE ---
st.title("⚖️ Risk & Volume Analysis")
st.caption("Analyze trade performance by Lot Size to optimize risk efficiency.")

df = load_trades()

if df.empty:
    st.warning("No trade data found to analyze.")
    st.stop()

# Filters
with st.sidebar:
    st.header("Graph Filters")
    alias_map = get_account_names(df)
    df['account_label'] = df['account_id'].astype(str).map(lambda x: alias_map.get(x, x))
    
    all_accs = sorted(df['account_id'].unique())
    sel_accs_raw = st.multiselect(
        "Accounts", 
        all_accs, 
        default=all_accs, 
        format_func=lambda x: alias_map.get(str(x), str(x))
    )
    
    sel_eas = st.multiselect("EAs", sorted(df['ea_name'].unique()), default=df['ea_name'].unique())
    sel_pairs = st.multiselect("Symbols", sorted(df['symbol'].unique()), default=df['symbol'].unique())

# Application
mask = (
    (df['account_id'].isin(sel_accs_raw)) &
    (df['ea_name'].isin(sel_eas)) &
    (df['symbol'].isin(sel_pairs))
)
filtered = df[mask].copy()

if filtered.empty:
    st.info("No trades match filters.")
    st.stop()

# --- ADVANCED ADVISOR LOGIC ---
def calculate_pf(sub_df):
    gross_profit = sub_df[sub_df['net_profit'] > 0]['net_profit'].sum()
    gross_loss = abs(sub_df[sub_df['net_profit'] < 0]['net_profit'].sum())
    return gross_profit / gross_loss if gross_loss > 0 else (999 if gross_profit > 0 else 0)

st.subheader("1. Profit vs Volume Overview")
c_chart, c_ai = st.columns([3, 1])

# Scatter Plot
with c_chart:

    color_col = 'account_label' if len(sel_accs_raw) > 1 else 'ea_name'
    fig = px.scatter(
        filtered, 
        x='volume', 
        y='net_profit', 
        color=color_col,
        hover_data=['ticket', 'symbol', 'close_time'],
        title="Trade Outcomes by Lot Size",
        trendline="ols",
        height=500
    )
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#888'),
        xaxis=dict(showgrid=False, title="Lot Size"),
        yaxis=dict(showgrid=True, gridcolor='#333', title="Net Profit ($)")
    )
    st.plotly_chart(fig, use_container_width=True)


# AI Advisor
with c_ai:
    st.write("### 🤖 Advanced Advisor")
    
    # Logic Buckets
    small_trades = filtered[filtered['volume'] < 0.1]
    large_trades = filtered[filtered['volume'] >= 0.1]
    
    pf_small = calculate_pf(small_trades)
    pf_large = calculate_pf(large_trades)
    
    advice_list = []
    
    # 1. Lot Size Cap Advice
    if not large_trades.empty and len(large_trades) > 5:
        if pf_large < 1.0 and pf_small > 1.1:
            advice_list.append({
                "type": "danger",
                "title": "Cap Your Lots!",
                "msg": f"Small trades (<0.1) are profitable (PF {pf_small:.2f}), but large trades are losing money (PF {pf_large:.2f}). **Action: Reduce Max Lot to 0.09.**"
            })
        elif pf_large > 1.5 and pf_large > pf_small:
            advice_list.append({
                "type": "safe",
                "title": "Scale Up",
                "msg": f"Your large trades (>0.1) are highly effective (PF {pf_large:.2f}). Consider increasing volume on winning pairs."
            })
            
    # 2. Specific Losers
    lot_stats = filtered.groupby('volume').agg(
        pnl=('net_profit', 'sum'),
        count=('ticket', 'count')
    ).reset_index()
    worst_lot = lot_stats.sort_values('pnl').iloc[0]
    if worst_lot['pnl'] < -100 and worst_lot['count'] > 3:
        advice_list.append({
            "type": "danger",
            "title": f"Avoid {worst_lot['volume']} Lots",
            "msg": f"This specific size has lost ${worst_lot['pnl']:,.2f} over {worst_lot['count']} trades. It may be hitting liquidity issues or bad EA settings."
        })

    if not advice_list:
        st.info("Performance is consistent across lot sizes. Keep monitoring.")
    else:
        for item in advice_list:
            bg_color = "#ffcccc" if item['type'] == 'danger' else "#ccffcc"
            border_color = "#ff0000" if item['type'] == 'danger' else "#00ff00"
            text_color = "#333333" # Force dark text for readability
            
            st.markdown(f"""
            <div style="background-color: {bg_color}; border-left: 5px solid {border_color}; padding: 10px; margin-bottom: 10px; border-radius: 5px; color: {text_color};">
                <strong style="color: {text_color};">{item['title']}</strong><br>
                {item['msg']}
            </div>
            """, unsafe_allow_html=True)
            
    with st.expander("📊 Data Support"):
        st.write(f"**Small Lots (<0.1)**: PF {pf_small:.2f} ({len(small_trades)} trades)")
        st.write(f"**Large Lots (>= 0.1)**: PF {pf_large:.2f} ({len(large_trades)} trades)")



# --- BUCKET ANALYSIS ---
st.subheader("2. Deep Dive: Performance by Lot Category")


bins = [0, 0.01, 0.05, 0.10, 0.50, 1.0, 100.0]
labels = ["Micro (0.01)", "Tiny (0.02-0.05)", "Small (0.06-0.10)", "Medium (0.11-0.50)", "High (0.51-1.0)", "Whale (1.0+)"]

filtered['lot_bucket'] = pd.cut(filtered['volume'], bins=bins, labels=labels, right=True)

bucket_stats = filtered.groupby('lot_bucket', observed=False).agg(
    Trades=('ticket', 'count'),
    Net_Profit=('net_profit', 'sum'),
    Profit_Factor=('net_profit', lambda x: calculate_pf(filtered.loc[x.index])),
    Win_Rate=('net_profit', lambda x: ((x > 0).sum() / len(x) * 100) if len(x) > 0 else 0)
).reset_index()

bucket_stats = bucket_stats[bucket_stats['Trades'] > 0]

c1, c2 = st.columns([2, 1])

with c1:
    fig_bar = px.bar(
        bucket_stats, 
        x='lot_bucket', 
        y='Net_Profit', 
        color='Net_Profit',
        color_continuous_scale='RdYlGn',
        title="Net Profit by Category",
        text_auto='.2s'
    )
    fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#888'))
    st.plotly_chart(fig_bar, use_container_width=True)

with c2:
    st.dataframe(
        bucket_stats.style.format({
            "Net_Profit": "${:,.2f}",
            "Profit_Factor": "{:.2f}",
            "Win_Rate": "{:.1f}%"
        }),
        use_container_width=True,
        hide_index=True
    )


