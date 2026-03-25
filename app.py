
import streamlit as st
import time
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import traceback

# Import custom modules
import data_manager
import predictor
import news_manager

# --- Page and Style Configuration ---
st.set_page_config(page_title="Crypto Predictor Pro", layout="wide", page_icon="💹", initial_sidebar_state="expanded")

# --- COMPLETE UI STYLESHEET OVERHAUL ---
st.markdown("""
<style>
    /* --- MASTER THEME --- */
    .stApp {
        background-color: #0E1117; /* Main app background */
        color: #FAFAFA; /* Bright default text */
    }

    /* --- SIDEBAR --- */
    div[data-testid="stSidebarUserContent"] {
         background-color: #1A202C; /* Distinct sidebar background */
         border-right: 2px solid #2D3748;
         padding: 1.5rem;
    }
    div[data-testid="stSidebarUserContent"] h1,
    div[data-testid="stSidebarUserContent"] h3,
    div[data-testid="stSidebarUserContent"] small,
    div[data-testid="stSidebarUserContent"] label {
        color: #E2E8F0 !important; /* Brighter text in sidebar */
        text-shadow: 0 0 5px rgba(0, 210, 255, 0.3);
    }
    div[data-testid="stSelectbox"] label,
    div[data-testid="stNumberInput"] label {
        color: #A0AEC0 !important; /* Softer color for labels */
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 0.8rem;
    }

    /* --- MAIN CONTENT --- */
    h1, h2, h3 { color: #E2E8F0 !important; }
    h1[style*="text-align: center"] { text-shadow: 0 0 10px rgba(0, 210, 255, 0.5); }
    p[style*="text-align: center"] { color: #A0AEC0 !important; }

    /* METRICS */
    div[data-testid="stMetric"] {
        background-color: #1A202C;
        border: 1px solid #2D3748;
        border-radius: 8px;
        padding: 1rem;
    }
    div[data-testid="stMetricLabel"] { color: #A0AEC0 !important; }
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        color: #00d2ff !important;
    }
    div[data-testid="stMetricDelta"] { font-weight: 700 !important; }

    /* --- CRITICAL FIX: TEXT AREAS (LOGS & AI REASONING) --- */
    div[data-testid="stTextArea"] textarea {
        background-color: #1A202C !important;
        color: #FAFAFA !important; /* Bright text */
        border: 1px solid #2D3748 !important;
        border-radius: 8px !important;
        font-family: 'monospace', mono; /* Monospaced for logs */
        font-size: 0.9rem;
        -webkit-text-fill-color: #FAFAFA !important; /* Force text color when disabled */
    }

    /* Hide Streamlit elements */
    #MainMenu, header, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# --- Session State Initialization ---
for key, default_value in [
    ("is_running", False), ("selected_coin", "BTC"),
    ("historical_df", pd.DataFrame()), ("session_df", pd.DataFrame()),
    ("plot_prices", []), ("logs", []),
    ("reasoning_text", "Awaiting data...")
]:
    if key not in st.session_state:
        st.session_state[key] = default_value

def log_msg(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.insert(0, f"[{ts}] {msg}")
    st.session_state.logs = st.session_state.logs[:50]

# --- Sidebar UI ---
with st.sidebar:
    st.title("CryptoBot Pro")
    st.markdown("---")

    selected_coin_from_ui = st.selectbox("ASSET", ["BTC", "ETH"], index=["BTC", "ETH"].index(st.session_state.selected_coin), key="sb_coin")
    if selected_coin_from_ui != st.session_state.selected_coin:
        st.session_state.selected_coin = selected_coin_from_ui
        st.session_state.is_running = False
        st.session_state.historical_df = pd.DataFrame()
        st.session_state.plot_prices, st.session_state.session_df = [], pd.DataFrame()
        log_msg(f"Switched asset to {selected_coin_from_ui}. Press START to begin.")
        st.rerun()

    timeframe_map = {"30m": 30, "1h": 60, "1d": 1440, "1w": 10080}
    timeframe_choice = st.selectbox("PREDICTION TARGET", list(timeframe_map.keys()) + ["Custom"], key="sb_timeframe")
    target_minutes = timeframe_map.get(timeframe_choice, 0)
    if timeframe_choice == "Custom":
        target_minutes = st.number_input("Custom Minutes:", min_value=1, value=45, key="sb_custom_mins")

    st.markdown("---")
    st.markdown("### 🚦 Controls")

    if st.session_state.is_running:
        if st.button("🔴 STOP TRACKING", use_container_width=True, key="btn_stop"):
            st.session_state.is_running = False
            log_msg("Tracking stopped by user.")
            st.rerun()
    else:
        if st.button("🟢 START TRACKING", use_container_width=True, key="btn_start"):
            st.session_state.plot_prices, st.session_state.logs, st.session_state.session_df = [], [], pd.DataFrame()
            log_msg("Initializing session...")
            if st.session_state.historical_df.empty:
                log_msg(f"Loading 1-Year History for {st.session_state.selected_coin}...")
                with st.spinner(f"Fetching 1-Year historical data..."):
                    try:
                        st.session_state.historical_df = data_manager.get_historical_data(st.session_state.selected_coin)
                        log_msg(f"Loaded {len(st.session_state.historical_df)} days of history.")
                    except Exception as e:
                        log_msg(f"FATAL ERROR on data fetch. App stopped.")
                        st.session_state.is_running = False
                        st.exception(e)
                        st.rerun()
            if not st.session_state.historical_df.empty:
                st.session_state.is_running = True
                st.rerun()

    st.markdown("---")
    st.markdown("**System Logs**")
    st.text_area("log_output", "\n".join(st.session_state.logs), height=200, key="log_area", disabled=True, label_visibility="collapsed")

# --- Main Dashboard UI ---
st.markdown("<h1 style='text-align: center; color: #00d2ff;'>⚡ LIVE MARKET DASHBOARD</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0AEC0; margin-bottom: 2rem;'>AI-Powered Cryptocurrency Forecasting & Order Flow Analysis</p>", unsafe_allow_html=True)

metric_col1, metric_col2, metric_col3 = st.columns(3)
price_placeholder = metric_col1.empty()
pred_placeholder = metric_col2.empty()
sentiment_placeholder = metric_col3.empty()

price_placeholder.metric("Current Price", "--- USD")
pred_placeholder.metric(f"Forecast ({target_minutes}m)", "--- USD")
sentiment_placeholder.metric("Market Sentiment", "---")

st.markdown("---")
col_chart, col_reason = st.columns([2, 1])

with col_chart:
    st.subheader("Live Price Chart")
    chart_placeholder = st.empty()

with col_reason:
    st.subheader("AI Analysis & Reasoning")
    reasoning_placeholder = st.empty()
    reasoning_placeholder.text_area("reasoning_output", st.session_state.reasoning_text, height=350, key="reasoning_area", disabled=True, label_visibility="collapsed")

# --- Main Application Loop ---
if st.session_state.is_running:
    try:
        loop_start = time.time()
        coin = st.session_state.selected_coin
        score, _ = news_manager.get_sentiment()
        price, source = data_manager.fetch_current_price(coin)

        if price:
            st.session_state.plot_prices.append(price)
            st.session_state.plot_prices = st.session_state.plot_prices[-60:]
            new_row = {"Timestamp": datetime.now(), "Price": price, "Coin": coin}
            st.session_state.session_df = pd.concat([st.session_state.session_df, pd.DataFrame([new_row])], ignore_index=True)
            
            sentiment = news_manager.manager.sentiment_score
            pred_val, ai_reasoning = predictor.analyze_and_predict(st.session_state.historical_df, st.session_state.session_df, target_minutes, sentiment)
            st.session_state.reasoning_text = ai_reasoning if pred_val else "AI is gathering initial data to build a stable forecast. Prediction will appear here shortly..."

        sentiment_placeholder.metric("Market Sentiment", f"{score:+.2f}")
        if price:
            price_placeholder.metric(f"Current Price ({coin})", f"${price:,.2f}")
            fig, ax = plt.subplots(figsize=(8, 4))
            
            if pred_val:
                delta = pred_val - price
                pred_placeholder.metric(f"Forecast ({target_minutes}m)", f"${pred_val:,.2f}", f"{delta:+.2f} USD")
                ax.axhline(y=pred_val, color='yellow', linestyle=':', linewidth=2, zorder=5, label=f"Forecast: ${pred_val:,.2f}")
            else:
                pred_placeholder.metric(f"Forecast ({target_minutes}m)", "Gathering data...")

            prices = st.session_state.plot_prices
            fig.patch.set_facecolor('#0E1117')
            ax.set_facecolor('#0E1117')
            ax.plot(prices, color='#00d2ff', linewidth=2, zorder=3)
            
            x = np.arange(len(prices))
            y = np.array(prices)
            ax.fill_between(x, y, color='#00d2ff', alpha=0.1, zorder=2)
            
            ax.grid(True, which='both', linestyle='--', linewidth=0.5, color='#4A5568', zorder=1)
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')
            
            for spine in ax.spines.values():
                spine.set_edgecolor('#2D3748')
            
            ax.set_ylabel("Price (USD)", color='white')
            ax.set_xlabel("Time (Recent Updates)", color='white')

            if prices:
                ax.axhline(y=prices[-1], color='red', linestyle='--', linewidth=1, zorder=4, label=f"Current: ${prices[-1]:,.2f}")
            
            # --- IMPROVED CHART LEGEND ---
            ax.legend(prop={'weight': 'bold', 'size': 'small'}, frameon=True, facecolor='#1A202C', edgecolor='#2D3748', labelcolor='white')
            
            chart_placeholder.pyplot(fig)
            plt.close(fig)

        reasoning_placeholder.text_area("reasoning_output", st.session_state.reasoning_text, height=350, key="reasoning_area_updated", disabled=True, label_visibility="collapsed")

    except Exception as e:
        log_msg("FATAL ERROR: Tracking stopped.")
        st.session_state.is_running = False
        st.exception(e)
        
    elapsed = time.time() - loop_start
    time.sleep(max(0.1, 15.0 - elapsed))
    st.rerun()
