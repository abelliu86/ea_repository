import streamlit as st

THEMES = {
    "Modern Pro": {
        "bg_color": "#0e1117",
        "card_bg": "#1e1e24",
        "text_color": "#e0e0e0",
        "accent_color": "#ff4b4b",
        "success_bg": "#0e2c1a",
        "success_border": "#00c853",
        "danger_bg": "#2c0b0e",
        "danger_border": "#ff4b4b",
        "font": "'Source Sans Pro', sans-serif"
    },
    "Institutional": {
        "bg_color": "#000000",
        "card_bg": "#1a1a1a",
        "text_color": "#ffb74d", # Amber
        "accent_color": "#ff9800",
        "success_bg": "#1a2e1a",
        "success_border": "#4caf50",
        "danger_bg": "#2e1a1a",
        "danger_border": "#f44336",
        "font": "'Courier New', monospace" # Terminal feel
    },
    "Oceanic": {
        "bg_color": "#001e26",
        "card_bg": "#002b36",
        "text_color": "#839496",
        "accent_color": "#2aa198",
        "success_bg": "#003b36",
        "success_border": "#2aa198",
        "danger_bg": "#3b0005",
        "danger_border": "#dc322f",
        "font": "-apple-system, BlinkMacSystemFont, sans-serif"
    },
    "Light Mode": {
        "bg_color": "#ffffff",
        "card_bg": "#f8f9fa",
        "text_color": "#31333f",
        "accent_color": "#ff4b4b",
        "success_bg": "#e6ffea",
        "success_border": "#00a12e",
        "danger_bg": "#ffe6e6",
        "danger_border": "#ff4b4b",
        "font": "'Source Sans Pro', sans-serif"
    }
}
DEFAULT_THEME = "Light Mode"

def apply_theme(theme_name=DEFAULT_THEME):
    """Injects CSS for the selected theme."""
    theme = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
    
    css = f"""
    <style>
        :root {{
            --bg-color: {theme['bg_color']};
            --card-bg: {theme['card_bg']};
            --text-color: {theme['text_color']};
            --accent-color: {theme['accent_color']};
            --success-bg: {theme['success_bg']};
            --success-border: {theme['success_border']};
            --danger-bg: {theme['danger_bg']};
            --danger-border: {theme['danger_border']};
        }}
        
        /* Global Background & Text */
        .stApp {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: {theme['font']};
        }}
        
        h1, h2, h3, h4, h5, h6, p, li, span, div {{
            color: var(--text-color) !important;
        }}
        
        /* Metric Cards */
        .metric-card {{
            background-color: var(--card-bg);
            padding: 20px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            margin-bottom: 20px;
        }}
        
        /* Advisor Boxes */
        .recommendation-box {{
            padding: 15px 20px;
            background-color: var(--danger-bg);
            border-left: 4px solid var(--danger-border);
            margin-bottom: 12px;
            border-radius: 4px;
            color: #eeeeee !important; /* Force readable text on colored box */
        }}
        
        .safe-box {{
            padding: 15px 20px;
            background-color: var(--success-bg);
            border-left: 4px solid var(--success_border);
            margin-bottom: 12px;
            border-radius: 4px;
            color: #eeeeee !important;
        }}
        
        /* Streamlit overrides */
        /* Streamlit overrides */
        [data-testid="stSidebar"] {{
            background-color: var(--card-bg);
            border-right: 1px solid rgba(255,255,255,0.1);
        }}
        [data-testid="stSidebar"] * {{
            background-color: transparent; /* Fix for nested elements */
        }}
        
        /* Scrollbars */
        ::-webkit-scrollbar {{
            width: 10px;
            background: var(--bg_color);
        }}
        ::-webkit-scrollbar-thumb {{
            background: var(--accent-color);
            border-radius: 5px;
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def card_container():
    """Helper to start a card container div (End with st.markdown('</div>', ...))"""
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)

def card_end():
    st.markdown('</div>', unsafe_allow_html=True)
