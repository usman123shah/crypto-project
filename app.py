import streamlit as st
import time
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

# Import custom modules
import data_manager
import predictor
import news_manager

# Streamlit Page Configuration
st.set_page_config(page_title="Crypto Predictor Pro", layout="wide", page_icon="💹", initial_sidebar_state="expanded")

# Hide Streamlit Default Elements (Menu, Header, Footer)
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom Styling for Metrics */
    div[data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 800 !important;
        color: #00d2ff !important;
    }
    
    /* Box shadows for main elements */
    .stTextArea textarea {
        background-color: #12161A !important;
        color: #E2E8F0 !important;
        border: 1px solid #2D3748 !important;
        border-radius: 8px !important;
    }
    
    h1, h2, h3 {
        color: #E2E8F0 !important;
    }
    
</style>
""", unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE ---
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "selected_coin" not in st.session_state:
    st.session_state.selected_coin = "BTC"
if "historical_df" not in st.session_state:
    st.session_state.historical_df = pd.DataFrame()
if "session_df" not in st.session_state:
    st.session_state.session_df = pd.DataFrame()
if "plot_prices" not in st.session_state:
    st.session_state.plot_prices = []
if "logs" not in st.session_state:
    st.session_state.logs = []

def log_msg(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.insert(0, f"[{ts}] {msg}")
    if len(st.session_state.logs) > 50:
        st.session_state.logs.pop()

# --- SIDEBAR UI ---
with st.sidebar:
    st.title("CryptoBot Pro")
    st.markdown("---")
    
    selected_coin = st.selectbox("ASSET", ["BTC", "ETH"], index=0 if st.session_state.selected_coin == "BTC" else 1)
    
    timeframe_choice = st.selectbox("PREDICTION TARGET", ["30m", "1h", "1d", "1w", "Custom"])
    custom_mins = 0
    if timeframe_choice == "Custom":
        custom_mins = st.number_input("Custom Minutes:", min_value=1, value=45)
        
    def get_target_minutes():
        if timeframe_choice == "30m": return 30
        if timeframe_choice == "1h": return 60
        if timeframe_choice == "1d": return 1440
        if timeframe_choice == "1w": return 10080
        return custom_mins

    target_minutes = get_target_minutes()
    
    st.markdown("---")
    
    # Start / Stop Logic
    st.markdown("### 🚦 Controls")
    if st.session_state.is_running:
        if st.button("🔴 STOP TRACKING", use_container_width=True):
            st.session_state.is_running = False
            log_msg("Tracking stopped by user.")
            st.rerun()
    else:
        if st.button("🟢 START TRACKING", use_container_width=True):
            # Check if coin changed to reload history
            if st.session_state.selected_coin != selected_coin or st.session_state.historical_df.empty:
                 st.session_state.selected_coin = selected_coin
                 log_msg(f"Loading 1-Year History for {selected_coin}...")
                 try:
                     st.session_state.historical_df = data_manager.get_historical_data(selected_coin)
                     st.session_state.session_df = data_manager.load_data()
                     log_msg(f"Loaded {len(st.session_state.historical_df)} days of history.")
                 except Exception as e:
                     log_msg(f"Error loading history: {e}")
            
            st.session_state.plot_prices = [] # Reset plot for new session
            st.session_state.is_running = True
            log_msg("Started high-frequency tracking...")
            st.rerun()
            
    st.markdown("---")
    
    # Log Viewer
    st.markdown("**System Logs**")
    log_container = st.empty()
    log_container.text_area("System Logs", value="\n".join(st.session_state.logs), height=150, disabled=True, label_visibility="collapsed")

# --- MAIN UI ---
st.markdown("<h1 style='text-align: center; color: #00d2ff;'>⚡ LIVE MARKET DASHBOARD</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0AEC0; margin-bottom: 2rem;'>AI-Powered Cryptocurrency Forecasting & Order Flow Analysis</p>", unsafe_allow_html=True)

# Top Metrics Placeholders
metric_col1, metric_col2, metric_col3 = st.columns(3)
price_placeholder = metric_col1.empty()
pred_placeholder = metric_col2.empty()
sentiment_placeholder = metric_col3.empty()

price_placeholder.metric("Current Price", "--- USD")
pred_placeholder.metric(f"Forecast ({target_minutes}m)", "--- USD")
sentiment_placeholder.metric("Market Sentiment", "---")

st.markdown("---")

# Chart and Reasoning layouts
col_chart, col_reason = st.columns([2, 1])

# Chart Placeholders
with col_chart:
    st.subheader("Live Tracking")
    chart_placeholder = st.empty()

with col_reason:
    st.subheader("AI Analysis & Reasoning")
    reasoning_placeholder = st.empty()
    reasoning_placeholder.text_area("AI Reasoning", "Awaiting data...", height=350, disabled=True, label_visibility="collapsed")


# --- LIVE LOOP ---
if st.session_state.is_running:
    try:
        # First, refresh news sentiment once
        try:
            score, reasoning = news_manager.get_sentiment()
            sentiment_placeholder.metric("Market Sentiment", f"{score:+.2f}")
        except Exception as e:
            sentiment_placeholder.metric("Market Sentiment", "Error")
            
        coin = st.session_state.selected_coin
        
        while st.session_state.is_running:
            loop_start = time.time()
            
            # 1. Fetch live price
            price, source = data_manager.fetch_current_price(coin)
            
            if price:
                # Update UI Metric
                price_placeholder.metric(f"Current Price ({coin})", f"${price:,.2f}")
                
                # Update plot data
                st.session_state.plot_prices.append(price)
                if len(st.session_state.plot_prices) > 60:
                    st.session_state.plot_prices.pop(0)
                    
                # Update Session Memory
                new_row = {"Timestamp": datetime.now(), "Price": price, "Coin": coin}
                temp_df = pd.DataFrame([new_row])
                if not st.session_state.session_df.empty:
                    st.session_state.session_df = pd.concat([st.session_state.session_df, temp_df], ignore_index=True)
                else:
                    st.session_state.session_df = temp_df
                    
                # 2. Predict
                sentiment = news_manager.manager.sentiment_score
                pred_val, ai_reasoning = predictor.analyze_and_predict(st.session_state.historical_df, st.session_state.session_df, target_minutes, sentiment)
                
                if pred_val:
                    delta = pred_val - price
                    pred_placeholder.metric(f"Forecast ({target_minutes}m)", f"${pred_val:,.2f}", f"{delta:+.2f} USD")
                    reasoning_placeholder.text_area("AI Analysis", ai_reasoning, height=350, disabled=True, label_visibility="collapsed")
                else:
                    pred_placeholder.metric(f"Forecast ({target_minutes}m)", "Gathering data...")
                    
                # 3. Render Chart
                fig, ax = plt.subplots(figsize=(8, 4))
                fig.patch.set_facecolor('#0E1117')
                ax.set_facecolor('#0E1117')
                ax.tick_params(colors='#A0AEC0', labelsize=9)
                ax.grid(True, color='#2D3748', linestyle=':', alpha=0.6)
                
                # Remove borders
                for spine in ax.spines.values():
                    spine.set_color('#2D3748')
                
                x_data = np.arange(len(st.session_state.plot_prices))
                
                # Actual Line (Vibrant Blue)
                ax.plot(x_data, st.session_state.plot_prices, color='#00d2ff', linewidth=2.5, label="Live Price")
                
                # Trend Line (Subtle Violet/Pink)
                if len(st.session_state.plot_prices) > 2:
                    coef = np.polyfit(x_data, st.session_state.plot_prices, 1)
                    poly1d_fn = np.poly1d(coef)
                    ax.plot(x_data, poly1d_fn(x_data), color='#9F7AEA', linestyle='--', linewidth=1.5, label="Micro-Trend", alpha=0.8)
                    
                # Prediction Line Element (Neon Green/Red depending on sentiment)
                if pred_val:
                    pred_color = '#48BB78' if pred_val > price else '#F56565'
                    curr_x = len(st.session_state.plot_prices) - 1
                    target_x = curr_x + (target_minutes * 60) # Visual approximation
                    ax.plot([curr_x, target_x], [price, pred_val], color=pred_color, linestyle=':', linewidth=2.5, label="AI Target")
                    
                    # Plot end dot
                    ax.scatter(target_x, pred_val, color=pred_color, s=40, zorder=5)
                    
                ax.legend(facecolor='#0E1117', edgecolor='#2D3748', labelcolor='#E2E8F0', loc='upper left', framealpha=0.8)
                chart_placeholder.pyplot(fig)
                plt.close(fig)
                
            # Update logs container
            log_container.text_area("Logs", value="\n".join(st.session_state.logs), height=150, disabled=True, label_visibility="collapsed")
            
            # Throttle fetch loop
            elapsed = time.time() - loop_start
            sleep_amount = max(0.1, 2.0 - elapsed) # Wait 2 seconds between updates to ease rendering UI
            time.sleep(sleep_amount)

    except Exception as e:
        # If any unexpected error occurs, hide traceback and notify cleanly.
        log_msg(f"System interupt handling stream. Re-syncing...")
        time.sleep(2)
        st.rerun()
