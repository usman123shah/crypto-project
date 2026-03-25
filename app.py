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

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 800 !important; color: #00d2ff !important; }
    .stTextArea textarea { background-color: #12161A !important; color: #E2E8F0 !important; border: 1px solid #2D3748 !important; border-radius: 8px !important; }
    h1, h2, h3 { color: #E2E8F0 !important; }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
for key, default_value in [
    ("is_running", False),
    ("selected_coin", "BTC"),
    ("historical_df", pd.DataFrame()),
    ("session_df", pd.DataFrame()),
    ("plot_prices", []),
    ("logs", [])
]:
    if key not in st.session_state:
        st.session_state[key] = default_value

def log_msg(msg):
    """Adds a timestamped message to the session log."""
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.insert(0, f"[{ts}] {msg}")
    st.session_state.logs = st.session_state.logs[:50] # Keep log size manageable

# --- Sidebar UI ---
with st.sidebar:
    st.title("CryptoBot Pro")
    st.markdown("---")
    
    selected_coin = st.selectbox("ASSET", ["BTC", "ETH"], index=["BTC", "ETH"].index(st.session_state.selected_coin), key="sb_coin")
    
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
            # --- SMART DATA LOADING AND SESSION CLEANUP ---
            st.session_state.plot_prices = [] 
            st.session_state.logs = []
            st.session_state.session_df = pd.DataFrame()
            log_msg("Initializing session...")

            # Load data ONLY if it's new or not present
            if st.session_state.selected_coin != selected_coin or st.session_state.historical_df.empty:
                st.session_state.selected_coin = selected_coin
                log_msg(f"Loading 1-Year History for {selected_coin}...")
                with st.spinner(f"Fetching 1-Year historical data for {selected_coin}..."):
                    try:
                        st.session_state.historical_df = data_manager.get_historical_data(selected_coin)
                        log_msg(f"Loaded {len(st.session_state.historical_df)} days of history.")
                    except Exception as e:
                        log_msg(f"FATAL ERROR on data fetch. App stopped.")
                        st.session_state.is_running = False
                        st.exception(e) # Display the full error on the page
                        st.rerun() 
            else:
                log_msg("Using cached historical data.")
            
            if not st.session_state.historical_df.empty:
                st.session_state.is_running = True
                log_msg("Started high-frequency tracking...")
                st.rerun()

    st.markdown("---")
    st.markdown("**System Logs**")
    log_container = st.empty()
    log_container.text_area("log_output", "\n".join(st.session_state.logs), height=200, key="log_area", disabled=True, label_visibility="collapsed")

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
    st.subheader("Live Tracking")
    chart_placeholder = st.empty()

with col_reason:
    st.subheader("AI Analysis & Reasoning")
    reasoning_placeholder = st.empty()
    reasoning_placeholder.text_area("reasoning_output", "Awaiting data...", height=350, key="reasoning_area", disabled=True, label_visibility="collapsed")

# --- ROBUST LIVE LOOP ---
if st.session_state.is_running:
    try:
        # Initial news sentiment fetch
        score, reasoning = news_manager.get_sentiment()
        sentiment_placeholder.metric("Market Sentiment", f"{score:+.2f}")
        
        coin = st.session_state.selected_coin
        
        while st.session_state.is_running:
            loop_start = time.time()
            price, source = data_manager.fetch_current_price(coin)
            
            if price:
                price_placeholder.metric(f"Current Price ({coin})", f"${price:,.2f}")
                st.session_state.plot_prices.append(price)
                st.session_state.plot_prices = st.session_state.plot_prices[-60:]
                
                new_row = {"Timestamp": datetime.now(), "Price": price, "Coin": coin}
                st.session_state.session_df = pd.concat([st.session_state.session_df, pd.DataFrame([new_row])], ignore_index=True)
                
                sentiment = news_manager.manager.sentiment_score
                pred_val, ai_reasoning = predictor.analyze_and_predict(st.session_state.historical_df, st.session_state.session_df, target_minutes, sentiment)
                
                if pred_val:
                    delta = pred_val - price
                    pred_placeholder.metric(f"Forecast ({target_minutes}m)", f"${pred_val:,.2f}", f"{delta:+.2f} USD")
                    reasoning_placeholder.text_area("reasoning_output", ai_reasoning, height=350, key="reasoning_area", disabled=True, label_visibility="collapsed")
                else:
                    pred_placeholder.metric(f"Forecast ({target_minutes}m)", "Gathering data...")
                
                # --- Chart Drawing Logic ---
                fig, ax = plt.subplots(figsize=(8, 4))
                fig.patch.set_facecolor('#0E1117')
                ax.set_facecolor('#0E1117')
                ax.tick_params(colors='#A0AEC0', labelsize=9)
                ax.grid(True, color='#2D3748', linestyle=':', alpha=0.6)
                for spine in ax.spines.values(): spine.set_color('#2D3748')
                
                x_data = np.arange(len(st.session_state.plot_prices))
                ax.plot(x_data, st.session_state.plot_prices, color='#00d2ff', linewidth=2.5, label="Live Price")
                
                if len(st.session_state.plot_prices) > 2:
                    coef = np.polyfit(x_data, st.session_state.plot_prices, 1)
                    poly1d_fn = np.poly1d(coef)
                    ax.plot(x_data, poly1d_fn(x_data), color='#9F7AEA', linestyle='--', linewidth=1.5, label="Micro-Trend", alpha=0.8)
                
                if pred_val:
                    pred_color = '#48BB78' if pred_val > price else '#F56565'
                    curr_x = len(st.session_state.plot_prices) - 1
                    target_x = curr_x + (target_minutes * 2) # Visual approximation of intervals
                    ax.plot([curr_x, target_x], [price, pred_val], color=pred_color, linestyle=':', linewidth=2.5, label="AI Target")
                    ax.scatter(target_x, pred_val, color=pred_color, s=40, zorder=5)
                
                ax.legend(facecolor='#0E1117', edgecolor='#2D3748', labelcolor='#E2E8F0', loc='upper left', framealpha=0.8)
                chart_placeholder.pyplot(fig)
                plt.close(fig)
                
            log_container.text_area("log_output", "\n".join(st.session_state.logs), height=200, key="log_area", disabled=True, label_visibility="collapsed")
            
            elapsed = time.time() - loop_start
            time.sleep(max(0.1, 2.0 - elapsed))

    except Exception as e:
        # --- ROBUST ERROR HANDLING ---
        log_msg(f"FATAL ERROR: Execution stopped. See details below.")
        st.session_state.is_running = False
        st.exception(e) # Display the full exception in the app
        log_container.text_area("log_output", "\n".join(st.session_state.logs), height=200, key="log_area", disabled=True, label_visibility="collapsed")
        st.stop() # Stop the script immediately to prevent rerun loop
